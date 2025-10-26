import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    directURL = PAsearchSites.getSearchSearchURL(siteNum) + searchData.title.replace(' ', '-').lower()

    searchResults = [directURL]
    googleResults = PAutils.getFromSearchEngine(searchData.title, siteNum)
    for sceneURL in googleResults:
        if ('/scenes/' in sceneURL and sceneURL not in searchResults):
            searchResults.append(sceneURL)

    for sceneURL in searchResults:
        req = PAutils.HTTPRequest(sceneURL)
        if req.ok:
            detailsPageElements = HTML.ElementFromString(req.text)
            curID = PAutils.Encode(sceneURL)
            titleNoFormatting = detailsPageElements.xpath('//h1')[0].text_content().strip()
            releaseDate = parse(detailsPageElements.xpath('//time/@datetime')[0]).strftime('%Y-%m-%d')

            Log("directURL: " + str(directURL))
            Log("sceneURL: " + str(sceneURL))
            if directURL == sceneURL:
                score = 100
            elif searchData.date:
                score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
            else:
                score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

            results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, movieCollections, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneURL
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = detailsPageElements.xpath('//h1')[0].text_content().strip()

    # Summary
    maybeSummary = detailsPageElements.xpath('//p[contains(@class, "_s1jg1wcd75")]')
    if maybeSummary and len(maybeSummary) > 0:
        summary = []
        for summaryPart in maybeSummary:
            summaryText = summaryPart.text_content().strip()
            if 'Video specifications' not in summaryText:
                summary.append(summaryText)
        metadata.summary = '\n'.join(summary)

    # Studio
    metadata.studio = detailsPageElements.xpath('//a[contains(@class, "_euacs6n160")]')[0].text_content().strip()

    # Tagline and Collection(s)
    movieCollections.addCollection(metadata.studio)

    # Release Date
    maybeDate = detailsPageElements.xpath('//p[contains(@class, "_38471wcd31")]/time/@datetime')[0]
    if maybeDate:
        date_object = parse(maybeDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    for genreName in detailsPageElements.xpath('//a[contains(@class, "_1xdu1wcd88 ")]/span'):
        movieGenres.addGenre(genreName.text_content().strip())

    # Actor(s)
    actors = detailsPageElements.xpath('//a[contains(@class, "_n7wm1ua719")]')
    for actor in actors:
        actorName = actor.text_content().strip()
        actorLink = actor.xpath('./@href')[0]
        actorPageURL = PAsearchSites.getSearchBaseURL(siteNum) + actorLink

        req = PAutils.HTTPRequest(actorPageURL)
        actorPage = HTML.ElementFromString(req.text)
        actorPhotoURL = ''
        maybeActorPhotoURL = actorPage.xpath('//div[contains(@class, "_z763mqyu24 avatar avatar-size-32 outlined")]/img/@src')
        if len(maybeActorPhotoURL) > 0:
            actorPhotoURL = maybeActorPhotoURL[0]
        movieActors.addActor(actorName, actorPhotoURL)

    # Posters/Background
    xpaths = [
        '//meta[@property="og:image"]/@content',
        '//img[contains(@class, "_30hk1wta22")]/@src',
    ]

    for xpath in xpaths:
        for poster in detailsPageElements.xpath(xpath):
            art.append(poster)

    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl.replace('.webp', '.jpg'))
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100 and idx > 1:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
