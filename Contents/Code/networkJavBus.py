import PAsearchSites
import PAutils
import operator

cookies = {
    'existmag': 'all',
    'dv': '1'
}


def search(results, lang, siteNum, searchData):
    searchJAVID = None
    splitSearchTitle = searchData.title.split()
    if len(splitSearchTitle) > 1:
        if unicode(splitSearchTitle[1], 'UTF-8').isdigit():
            searchJAVID = '%s%%2B%s' % (splitSearchTitle[0], splitSearchTitle[1])
            directJAVID = '%s-%s' % (splitSearchTitle[0], splitSearchTitle[1])

    if searchJAVID:
        searchData.encoded = searchJAVID

    searchTypes = [
        'Censored',
        'Uncensored',
    ]

    for searchType in searchTypes:
        if searchType == 'Uncensored':
            sceneURL = PAsearchSites.getSearchSearchURL(siteNum) + 'uncensored/search/' + searchData.encoded
        elif searchType == 'Censored':
            sceneURL = PAsearchSites.getSearchSearchURL(siteNum) + 'search/' + searchData.encoded

        req = PAutils.HTTPRequest(sceneURL, cookies=cookies, allow_redirects=False)
        searchResults = HTML.ElementFromString(req.text)
        for searchResult in searchResults.xpath('//a[@class="movie-box"]'):
            titleNoFormatting = searchResult.xpath('.//span[1]')[0].text_content().replace('\t', '').replace('\r\n', '').strip()
            JAVID = searchResult.xpath('.//date[1]')[0].text_content().strip()

            sceneURL = searchResult.xpath('./@href')[0]
            curID = PAutils.Encode(sceneURL)

            if searchJAVID:
                score = 100 - Util.LevenshteinDistance(searchJAVID.lower(), JAVID.lower())
            else:
                score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

            results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='[%s][%s] %s' % (searchType, JAVID, titleNoFormatting), score=score, lang=lang))

    if directJAVID:
        sceneURL = PAsearchSites.getSearchSearchURL(siteNum) + directJAVID
        req = PAutils.HTTPRequest(sceneURL, cookies=cookies, allow_redirects=False)
        searchResult = HTML.ElementFromString(req.text)
        javTitle = searchResult.xpath('//head/title')[0].text_content().strip().replace(' - JavBus', '')
        if directJAVID.replace('-', '').replace('_', '').replace(' ', '').isdigit():
            javTitle = javStudio + ' ' + javTitle
        curID = PAutils.Encode(sceneURL)
        score = 100
        if not operator.contains(javTitle, '404 Page Not Found!'):
            results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='[Direct][%s] %s' % (directJAVID, javTitle), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, movieCollections, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])

    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchSearchURL(siteNum) + sceneURL
    req = PAutils.HTTPRequest(sceneURL, cookies=cookies, allow_redirects=False)
    detailsPageElements = HTML.ElementFromString(req.text)
    JAVID = sceneURL.rsplit('/', 1)[1]

    # Title
    studio = ''
    javStudio = detailsPageElements.xpath('//p/a[contains(@href, "/studio/")]')
    if javStudio:
        studio = javStudio[0].text_content().strip()
    javTitle = detailsPageElements.xpath('//head/title')[0].text_content().strip().replace(' - JavBus', '')
    if JAVID.replace('-', '').replace('_', '').replace(' ', '').isdigit():
        javTitle = studio + ' ' + javTitle
    metadata.title = javTitle

    # Studio
    metadata.studio = studio

    #  Tagline and Collection(s)
    data = {}

    label = detailsPageElements.xpath('//p/a[contains(@href, "/label/")]')
    if label:
        data['Label'] = label[0].text_content().strip()

    series = detailsPageElements.xpath('//p/a[contains(@href, "/series/")]')
    if series:
        data['Series'] = series[0].text_content().strip()

    metadata.tagline = ', '.join(['%s: %s' % (key, value) for key, value in data.items()])
    if label:
        metadata.tagline = label[0].text_content().strip()
        movieCollections.addCollection(metadata.tagline)
    else:
        movieCollections.addCollection(metadata.studio)

    # Release Date
    dateOrigin = detailsPageElements.xpath('//div[@class="col-md-3 info"]/p[2]')[0].text_content()
    date = dateOrigin[dateOrigin.find(':')+2:]
    if date != '0000-00-00':
        date_object = datetime.strptime(date, '%Y-%m-%d')
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    for genreLink in detailsPageElements.xpath('//span[@class="genre"]//a[contains(@href, "/genre/")]'):
        genreName = genreLink.text_content().lower().strip()
        movieGenres.addGenre(genreName)

    # Actor(s)
    for actorLink in detailsPageElements.xpath('//a[@class="avatar-box"]'):
        fullActorName = actorLink.xpath('./div/img/@title')[0]
        actorPhotoURL = detailsPageElements.xpath('//a[@class="avatar-box"]/div[@class="photo-frame"]/img[contains(@title, "%s")]/@src' % (fullActorName))[0]
        if not actorPhotoURL.startswith('http'):
            actorPhotoURL = PAsearchSites.getSearchBaseURL(siteNum) + actorPhotoURL

        if actorPhotoURL.rsplit('/', 1)[1] == 'nowprinting.gif':
            actorPhotoURL = ''

        movieActors.addActor(fullActorName, actorPhotoURL)

    # Director
    directorLink = detailsPageElements.xpath('//p/a[contains(@href, "/director/")]')
    if directorLink:
        directorName = directorLink[0].text_content().strip()

        movieActors.addDirector(directorName, '')

    # Posters
    xpaths = [
        '//a[contains(@href, "/cover/")]/@href',
        '//a[@class="sample-box"]/@href',
        '//a[@class="bigImage"]/@href',
    ]
    coverImage = detailsPageElements.xpath('//a[contains(@href, "/cover/")]/@href')
    if coverImage:
        coverImageCode = coverImage[0].rsplit('/', 1)[1].split('.')[0].split('_')[0]
        imageHost = coverImage[0].rsplit('/', 2)[0]
        coverImage = imageHost + '/thumb/' + coverImageCode + '.jpg'
    else:
        coverImage = detailsPageElements.xpath('//a[@class="bigImage"]/@href')[0]
    if coverImage.count('/images.') == 1:
        coverImage = coverImage.replace('thumb', 'thumbs')

    if coverImage.count('pics.dmm.co.jp') == 1:
        coverImage = coverImage.replace('pl.jpg', 'ps.jpg')

    if not coverImage.startswith('http'):
        coverImage = PAsearchSites.getSearchBaseURL(siteNum) + coverImage

    art.append(coverImage)
    for xpath in xpaths:
        for poster in detailsPageElements.xpath(xpath):
            if not poster.startswith('http'):
                poster = PAsearchSites.getSearchBaseURL(siteNum) + poster

            art.append(poster)

    images = []
    posterExists = False
    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                headers = {}
                if posterUrl.count('www.javbus.com') == 1:
                    headers = {'Referer': 'https://www.javbus.com/'}
                fixedUrl = posterUrl.replace('www.prestige-av.com/images/corner/goods', 'image.mgstage.com/images')
                image = PAutils.HTTPRequest(fixedUrl, cookies=cookies, headers=headers)
                im = StringIO(image.content)
                images.append(image)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if height > width:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                    posterExists = True
                if width > height:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    if not posterExists:
        for idx, image in enumerate(images, 1):
            try:
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[art[idx - 1]] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
