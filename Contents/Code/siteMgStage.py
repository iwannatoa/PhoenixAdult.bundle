import PAsearchSites
import PAutils
import operator

cookies = {
    'adc': '1',
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

        sceneURL = PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded

        req = PAutils.HTTPRequest(sceneURL, cookies=cookies)
        searchResults = HTML.ElementFromString(req.text)
        for searchResult in searchResults.xpath('//div[@class="search_list"]//li'):
            titleNoFormatting = searchResult.xpath('.//p[@class="title lineclamp"]')[0].text_content().replace('\t', '').replace('\r\n', '').strip()
            sceneURL = searchResult.xpath('.//h5/@href')[0]
            JAVID = sceneURL.replace('/product/product_detail/', '').replace('/', '').strip()
            curID = PAutils.Encode(sceneURL)

            if searchJAVID:
                score = 100 - Util.LevenshteinDistance(searchJAVID.lower(), JAVID.lower())
            else:
                score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

            results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='[%s][%s] %s' % (searchType, JAVID, titleNoFormatting), score=score, lang=lang))

    if directJAVID:
        sceneURL = PAsearchSites.getSearchSearchURL(siteNum) + '/product/product_detail/' + directJAVID
        req = PAutils.HTTPRequest(sceneURL, cookies=cookies)
        searchResult = HTML.ElementFromString(req.text)
        if not operator.contains(searchResult.xpath('//head/title'), 'MGS動画'):
            javTitle = searchResult.xpath('//div[@class="common_detail_cover"]//h1')[0].text_content().strip()
            javTitle = directJAVID + ' ' + javTitle
            curID = PAutils.Encode(sceneURL)
            score = 100
            results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='[Direct][%s] %s' % (directJAVID, javTitle), score=score, lang=lang))
    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])

    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchSearchURL(siteNum) + sceneURL
    req = PAutils.HTTPRequest(sceneURL, cookies=cookies, allow_redirects=False)
    detailsPageElements = HTML.ElementFromString(req.text)
    JAVID = sceneURL.rsplit('/', 1)[1]

    # Title
    javStudio = detailsPageElements.xpath('//td/a[contains(@href, "maker")]')[0].text_content().strip()
    javTitle = detailsPageElements.xpath('//div[@class="common_detail_cover"]//h1')[0].text_content().strip()
    javTitle = JAVID + ' ' + javTitle
    metadata.title = javTitle

    # Studio
    metadata.studio = javStudio

    #  Tagline and Collection(s)
    data = {}

    label = detailsPageElements.xpath('//td/a[contains(@href, "label")]')
    if label:
        data['Label'] = label[0].text_content().strip()

    series = detailsPageElements.xpath('//td/a[contains(@href, "series")]')
    if series:
        data['Series'] = series[0].text_content().strip()

    metadata.tagline = ', '.join(['%s: %s' % (key, value) for key, value in data.items()])
    if label:
        metadata.tagline = label[0].text_content().strip()
        metadata.collections.add(metadata.tagline)
    else:
        metadata.collections.add(metadata.studio)

    # Release Date
    date = detailsPageElements.xpath('//table[2]/tbody/tr[5]/td')[0].text_content()
    # date = dateOrigin[dateOrigin.find(':')+2:]
    if date != '0000/00/00':
        date_object = datetime.strptime(date, '%Y/%m/%d')
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    for genreLink in detailsPageElements.xpath('//td/a[contains(@href, "genre")]'):
        genreName = genreLink.text_content().lower().strip()
        movieGenres.addGenre(genreName)

    # Actor(s)
    for actorLink in detailsPageElements.xpath('//div[@class="push_connect_list"]//div[@class="connect_cover"]/dl'):
        fullActorName = actorLink.xpath('./dd')[0].text_content()
        actorPhotoURL = detailsPageElements.xpath('./dt/img/@src')[0]
        if not actorPhotoURL.startswith('http'):
            actorPhotoURL = PAsearchSites.getSearchBaseURL(siteNum) + actorPhotoURL

        if actorPhotoURL.rsplit('/', 1)[1] == 'nowprinting.gif':
            actorPhotoURL = ''

        movieActors.addActor(fullActorName, actorPhotoURL)

    # Posters
    xpaths = [
        '//div[@class="detail_photo"]//img/@href',
        '//a[@id="EnlargeImage"]/@href'
        '//a[@class="sample_image"]/@href',
    ]
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
                image = PAutils.HTTPRequest(posterUrl)
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
