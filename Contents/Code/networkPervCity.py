import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    cookies = {'warning_cookie': '1'}
    searchResults = []

    googleResults = PAutils.getFromGoogleSearch(searchData.title, siteNum)
    for sceneURL in googleResults:
        sceneURL = sceneURL.replace('www.', '')
        if ('trailers' in sceneURL) and 'as3' not in sceneURL and sceneURL not in searchResults:
            searchResults.append(sceneURL)

    for sceneURL in searchResults:
        req = PAutils.HTTPRequest(sceneURL, cookies=cookies)
        detailsPageElements = HTML.ElementFromString(req.text)

        titleNoFormatting = detailsPageElements.xpath('//h1')[0].text_content().strip()
        try:
            subSite = detailsPageElements.xpath('//div[@class="about"]//h3')[0].text_content().replace('About', '').strip()
        except:
            subSite = ''
        curID = PAutils.Encode(sceneURL)

        date = ''
        if date:
            releaseDate = parse(date).strftime('%Y-%m-%d')
        else:
            releaseDate = searchData.dateFormat() if searchData.date else ''
        displayDate = releaseDate if date else ''

        if searchData.date and displayDate:
            score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
        else:
            score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [PervCity/%s]' % (titleNoFormatting, subSite) if subSite else '%s [PervCity]' % titleNoFormatting, score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, movieCollections, art):
    cookies = {'warning_cookie': '1'}
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])

    req = PAutils.HTTPRequest(sceneURL, cookies=cookies)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = PAutils.parseTitle(detailsPageElements.xpath('//h1')[0].text_content().strip(), siteNum)

    # Summary
    try:
        metadata.summary = detailsPageElements.xpath('//div[@class="infoBox clear"]/p')[0].text_content().strip()
    except:
        metadata.summary = detailsPageElements.xpath('//h3[@class="description"]')[0].text_content().strip()

    # Studio
    metadata.studio = 'PervCity'

    # Tagline and Collection(s)
    tagline = detailsPageElements.xpath('//div[@class="about"]//h3')
    if tagline:
        metadata.tagline = tagline[0].text_content().replace('About', '').strip()
        movieCollections.addCollection(metadata.tagline)
    elif PAsearchSites.getSearchSiteName(siteNum).replace(' ', '') != metadata.studio:
        metadata.tagline = PAsearchSites.getSearchSiteName(siteNum)
        movieCollections.addCollection(metadata.tagline)
    else:
        movieCollections.addCollection(metadata.studio)

    # Genres
    for genreLink in detailsPageElements.xpath('//div[@class="tagcats"]/a'):
        genreName = genreLink.text_content().strip()

        movieGenres.addGenre(genreName)

    # Actor(s)
    date = ''
    actors = detailsPageElements.xpath('//h2/span/a | //h3/span/a')
    for actorLink in actors:
        actorName = actorLink.text_content().strip()
        actorPhotoURL = ''

        try:
            modelURL = actorLink.xpath('.//@href')[0].replace(PAsearchSites.getSearchBaseURL(siteNum).replace('www.', ''), PAsearchSites.getSearchBaseURL(1165).replace('www.', ''))
            req = PAutils.HTTPRequest(modelURL, cookies=cookies)
            actorsPageElements = HTML.ElementFromString(req.text)
            actorPhotoURL = actorsPageElements.xpath('//div[@class="starPic" or @class="bioBPic"]/img/@src')[0]
        except:
            modelURL = actorLink.xpath('.//@href')[0].replace('www.', '')
            req = PAutils.HTTPRequest(modelURL, cookies=cookies)
            actorsPageElements = HTML.ElementFromString(req.text)
            actorPhotoURL = actorsPageElements.xpath('//div[@class="starPic" or @class="bioBPic"]/img/@src')[0]


        if not date:
            for scene in actorsPageElements.xpath('//div[@class="videoBlock" or @class="videoContent"]'):
                cleanTitle = re.sub(r'\W', '', metadata.title).lower()
                h2CleanTitle = re.sub(r'\W', '', scene.xpath('.//h3')[0].text_content().replace('...', '').strip()).lower()
                h3CleanTitle = re.sub(r'\W', '', scene.xpath('.//h2/a')[0].text_content().replace('...', '').strip()).lower()
                if h2CleanTitle in cleanTitle or h3CleanTitle in cleanTitle:
                    date = actorsPageElements.xpath('.//div[@class="date"]')[0].text_content()

            if date:
                date_object = parse(date)
                metadata.originally_available_at = date_object
                metadata.year = metadata.originally_available_at.year

        movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    xpaths = [
        '//div[@class="snap"]//@src0_3x',
    ]

    for xpath in xpaths:
        for img in detailsPageElements.xpath(xpath):
            if 'http' not in img:
                img = PAsearchSites.getSearchBaseURL(siteNum) + img

            art.append(img)

    Log('Artwork found: %d' % len(art))
    postersClean = list()
    for idx, posterUrl in enumerate(art, 1):
        # Remove Timestamp and Token from URL
        cleanUrl = posterUrl.split('?')[0]
        postersClean.append(cleanUrl)
        if not PAsearchSites.posterAlreadyExists(cleanUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl)
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[cleanUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100:
                    # Item is an art item
                    metadata.art[cleanUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    art.extend(postersClean)

    return metadata
