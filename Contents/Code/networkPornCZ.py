import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    searchData.encoded = searchData.title.replace(' ', '+').replace('--', '+').lower()
    req = PAutils.HTTPRequest(PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded)
    searchResults = HTML.ElementFromString(req.text)

    for searchResult in searchResults.xpath('//div[@data-type="video"]'):
        titleNoFormatting = PAutils.parseTitle(searchResult.xpath('.//div[@class="card-body"]/a')[0].text_content().strip(), siteNum)
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + searchResult.xpath('.//div[@class="card-body"]/a/@href')[0]
        curID = PAutils.Encode(sceneURL)

        releaseDate = searchData.dateFormat() if searchData.date else ''

        score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [PornCZ/%s]' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum)), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, movieCollections, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    sceneDate = metadata_id[2]

    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = PAutils.parseTitle(detailsPageElements.xpath('//h1')[0].text_content().strip(), siteNum)

    # Summary
    try:
        summary = detailsPageElements.xpath('//div[@class="dmb-1"]/p')[0].text_content().strip()
    except:
        summary = ''
    metadata.summary = summary

    # Studio
    metadata.studio = 'PornCZ'

    # Tagline and Collection(s)
    tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.tagline = tagline
    movieCollections.addCollection(tagline)

    # Release Date
    try:
        date = detailsPageElements.xpath('//meta[@property="video:release_date"]/@content')[0].strip()
        date_object = datetime.strptime(date, '%d.%m.%Y')
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year
    except:
        if sceneDate:
            date_object = parse(sceneDate)
            metadata.originally_available_at = date_object
            metadata.year = metadata.originally_available_at.year

    # Genres
    for genreLink in detailsPageElements.xpath('//div[contains(@class, "video-info")]//a[contains(@href, "?category=")]'):
        genreName = genreLink.text_content().split('#')[-1].strip()

        movieGenres.addGenre(genreName)

    # Actor(s)
    for actorLink in detailsPageElements.xpath('//div[@class="mini-avatars"]/a'):
        actorName = actorLink.text_content().strip()

        modelURL = PAsearchSites.getSearchBaseURL(siteNum) + actorLink.xpath('.//@href')[0]
        if 'http' not in modelURL:
            modelURL = PAsearchSites.getSearchBaseURL(siteNum) + modelURL

        req = PAutils.HTTPRequest(modelURL)
        modelsPageElements = HTML.ElementFromString(req.text)

        actorPhotoURL = modelsPageElements.xpath('//img[contains(@class, "actor-img")]/@data-src')[0]

        if 'blank' in actorPhotoURL:
            actorPhotoURL = ''
        elif 'http' not in actorPhotoURL:
            actorPhotoURL = PAsearchSites.getSearchBaseURL(siteNum) + actorPhotoURL

        gender = modelsPageElements.xpath('//div[contains(@class, "model-info__item")]/span[./i]')[0].text_content().lower().strip()
        if siteNum == 1215 and gender == 'female':
            actorName = '%s (Sex Doll)' % actorName

        movieActors.addActor(actorName, actorPhotoURL, gender=gender)

    # Posters
    xpaths = [
        '//a[@class="gallery-popup"]//@href',
        '//video[@class="video-player"]//@data-poster',
    ]

    for xpath in xpaths:
        for img in detailsPageElements.xpath(xpath):
            if 'http' not in img:
                img = PAsearchSites.getSearchBaseURL(siteNum) + img
            art.append(img)

    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl, headers={'Referer': PAsearchSites.getSearchBaseURL(siteNum)})
                im = StringIO(image.content)
                # resized_image = Image.open(im)
                metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
