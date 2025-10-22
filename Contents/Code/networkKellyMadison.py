import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    sceneID = None
    parts = searchData.title.split()
    if unicode(re.sub(r'^e(?=\d+$)', '', parts[0], flags=re.IGNORECASE), 'UTF-8').isdigit():
        sceneID = re.sub(r'^e(?=\d+$)', '', parts[0], flags=re.IGNORECASE)
        searchData.title = searchData.title.replace(parts[0], '', 1).strip()

    searchData.encoded = urllib.quote(searchData.title)
    searchUrl = '%s%s&type=episodes' % (PAsearchSites.getSearchSearchURL(siteNum), searchData.encoded)
    req = PAutils.HTTPRequest(searchUrl, cookies={'nats': 'MC4wLjMuNTguMC4wLjAuMC4w'})
    searchResults = HTML.ElementFromString(req.text)
    for searchResult in searchResults.xpath('//a[contains(@class, "video-card")]'):
        titleNoFormatting = searchResult.xpath('.//h3')[0].text_content().strip()

        sceneURL = searchResult.get('href')
        episodeID = searchResult.xpath('.//span[@class="video-title"]')[0].text_content().split('#')[-1].strip()
        searchID = sceneURL.split('/')[-1]
        subsite = searchResult.xpath('.//span[@class="badge badge-brand"]')[0].text_content().strip().replace('PF', 'PornFidelity').replace('TF', 'TeenFidelity').replace('KM', 'Kelly Madison')
        curID = PAutils.Encode(sceneURL)

        date = searchResult.xpath('.//time')
        if date:
            releaseDate = datetime.strptime(date[0].text_content().strip(), '%m/%d/%y').strftime('%Y-%m-%d')
        else:
            releaseDate = searchData.dateFormat() if searchData.date else ''
        displayDate = releaseDate if date else ''

        if sceneID and int(sceneID) == int(episodeID):
            score = 100
        elif sceneID and int(sceneID) == int(searchID):
            score = 100
        elif searchData.date:
            score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
        else:
            score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s] %s' % (titleNoFormatting, subsite, displayDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, movieCollections, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    sceneDate = metadata_id[2]
    if len(metadata_id) > 3:
        title = PAutils.Decode(metadata_id[3])
        searchResult = HTML.ElementFromString(PAutils.Decode(metadata_id[4]))
    req = PAutils.HTTPRequest(sceneURL, cookies={'nats': 'MC4wLjMuNTguMC4wLjAuMC4w'})
    detailsPageElements = HTML.ElementFromString(req.text)

    try:
        # Title
        metadata.title = PAutils.parseTitle(detailsPageElements.xpath('//h1[contains(@class, "title")]')[0].text_content().strip(), siteNum)

        # Summary
        metadata.summary = detailsPageElements.xpath('//div[contains(., "Episode Summary")]/p')[0].text_content().strip()

        # Studio
        metadata.studio = 'Kelly Madison Productions'

        # Actors
        actors = detailsPageElements.xpath('//p[contains(., "Starring")]//a[contains(@href, "/models/")]')
    except:
        # Title
        metadata.title = PAutils.parseTitle(title, siteNum)

        # Studio
        metadata.studio = 'Kelly Madison Productions'

        # Actors
        actors = searchResult.xpath('.//a[contains(@href, "/models/")]')

    # Tagline and Collection(s)
    if 'teenfidelity' in metadata.title.lower():
        tagline = 'TeenFidelity'
    elif 'kelly madison' in metadata.title.lower():
        tagline = 'Kelly Madison'
    else:
        tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.tagline = tagline
    movieCollections.addCollection(tagline)

    # Release Date
    date = detailsPageElements.xpath('//p[contains(., "Published")]/strong')
    if date:
        date_object = datetime.strptime(date[0].text_content().strip(), '%Y-%m-%d')
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year
    elif sceneDate:
        date_object = parse(sceneDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.addGenre('Hardcore')
    movieGenres.addGenre('Heterosexual')

    # Actor(s)
    if actors:
        if len(actors) == 3:
            movieGenres.addGenre('Threesome')
        if len(actors) == 4:
            movieGenres.addGenre('Foursome')
        if len(actors) > 4:
            movieGenres.addGenre('Orgy')

        for actorLink in actors:
            actorName = actorLink.text_content()

            actorPageURL = actorLink.get('href')
            req = PAutils.HTTPRequest(actorPageURL, cookies={'nats': 'MC4wLjMuNTguMC4wLjAuMC4w'})
            actorPage = HTML.ElementFromString(req.text)
            actorPhotoURL = actorPage.xpath('//div[contains(@class, "one")]//@src')[0]

            movieActors.addActor(actorName, actorPhotoURL)

    # Posters/Background
    art.append('https://tour-content-cdn.kellymadisonmedia.com/episode/poster_image/%s/poster.jpg' % sceneURL.rsplit('/')[-1])
    art.append('https://tour-content-cdn.kellymadisonmedia.com/episode/episode_thumb_image_1/%s/1.jpg' % sceneURL.rsplit('/')[-1])
    art.append('https://tour-content-cdn.kellymadisonmedia.com/episode/episode_thumb_image_1/%s/01.jpg' % sceneURL.rsplit('/')[-1])

    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl)
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
