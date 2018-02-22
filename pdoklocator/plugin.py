# -*- coding: utf-8 -*-

from qgis.core import QgsProject, QgsLocator, QgsLocatorFilter, QgsLocatorResult, \
                      QgsRectangle, QgsPoint, QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform

from .networkaccessmanager import NetworkAccessManager, RequestsException
from .pdoklocationserverclient import PdokLocationServerClient

import json


# QUESTION: should we create base classes for the GeocoderLocator and GeocoderFilter (in cpp or python)
# QUESTION: IF a service does not have a suggest-service (like Nominatim) adding a space ' ' at the end to force a search
# QUESTION: is a normal plugin the right thing to do?
# QUESTION: put 'name' in constructor of baseclass?
# QUESTION: should we have a cpp/python NetworkAccessManager(factory) somewhere?
# QUESTION: should a Filter already have a NAM and an iface
# QUESTION: if a geocoder filter needs to check crs (to reproject) or zoom in mapcanvas, where comes handle to mapcanvas from
# QUESTION: having different geocoder locators running: synchron or asynchron networking? (now I do synchro)
# QUESTION: why only 3 chars for prefix? (better make this configurable?)
# QUESTION: what to do with the zoomlevel of scale to zoom to? Always sent an extent? Or Extent + scale (better for TilingServices and then the locator can assure it is a nice map, or viewed on a suitable zoom level?)
#    would be cool to be able to have a object-type to scale mapping for all geocoders, so
#    you determine for every object type on which z-level (exact) you want to come...
# QUESTION: if you open te result again by just going to the search input and click after some time: segfault I think a nullpointer
# QUESTION: why short result texts with osm (missing the types)
# QUESTION: should the BaseGeocoderLocator set a point or label? As Option?



# TODO: handle network problems
# TODO: handle feedback from locatorfilter
# TODO: setting widget (for example for an (google) api key)

class GeocoderLocator:

    ADDRESS = 750
    STREET = 1500
    ZIP = 3000
    PLACE = 30000
    CITY = 120000
    ISLAND = 250000
    COUNTRY = 4000000

    def __init__(self, iface):

        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = iface.mapCanvas()

        self.filter = NominatimFilter(NetworkAccessManager(), self.iface)
        self.iface.registerLocatorFilter(self.filter)

        self.filter2 = PdokFilter(NetworkAccessManager(), self.iface)
        self.iface.registerLocatorFilter(self.filter2)

        self.c = PdokLocationServerClient()
        print(1)
        self.c.suggest('kaas')
        print(2)

    def unload(self):
        self.iface.deregisterLocatorFilter(self.filter)
        self.iface.deregisterLocatorFilter(self.filter2)

    def initGui(self):
        pass


class GeocoderFilter(QgsLocatorFilter):
    # trying out some kind of base class

    def __init__(self, nam, iface):
        super(QgsLocatorFilter, self).__init__()
        self.nam = nam
        self.iface = iface
        #print('constructor GeocoderFilter')

    def name(self):
        ##print('Calling name() van {}'.format(self.__class__.__name__))
        return self.__class__.__name__

    # def mapResult(self, coordinateArray_or_QgsGeometry):
    #     print
    #     if len(coordinateArray) == 2:
    #         #print('ZOOM TO POINT: {}'.format(coordinateArray))
    #     elif len(coordinateArray) == 4:
    #         #print('ZOOM TO EXTENT: {}'.format(coordinateArray))
    #     else:
    #         # TODO, message? Exception?
    #         pass


class NominatimFilter(GeocoderFilter):

    def __init__(self, nam, iface):
        super().__init__(nam, iface)
        #print('constructor NominatimFilter')

    # def name(self):
    #     ##print('Calling name() van NominatimFilter')
    #     return 'NominatimFilter'

    def clone(self):
        return NominatimFilter(self.nam, self.iface)

    def displayName(self):
        ##print('Calling displayName() van NominatimFilter')
        return 'Nominatim Geocoder (end with space to search)'

    def prefix(self):
        ##print('Calling prefix() van NominatimFilter')
        return 'osm'

    # def hasConfigWidget(self):
    #     return False
    #
    # # /**
    # #  * Returns true if the filter should be used when no prefix
    # #  * is entered.
    # #  * \see setUseWithoutPrefix()
    # #  */
    # def useWithoutPrefix(self):
    #     return False

    def fetchResults(self, search, context, feedback):
        # emit resultFetched() signal
        #  /**
        #  * Retrieves the filter results for a specified search \a string. The \a context
        #  * argument encapsulates the context relating to the search (such as a map
        #  * extent to prioritize).
        #  *
        #  * Implementations of fetchResults() should emit the resultFetched()
        #  * signal whenever they encounter a matching result.
        #  *
        #  * Subclasses should periodically check the \a feedback object to determine
        #  * whether the query has been canceled. If so, the subclass should return
        #  * this method as soon as possible.
        #  */
        ##print('--- NominatimFilter fetchResults called')
        ##print('NominatimFilter search: {}'.format(search))
        ##print('NominatimFilter context: {}'.format(context))
        #print('NominatimFilter context.targetExtent: {}'.format(context.targetExtent))
        #print('NominatimFilter context.targetExtentCrs: {}'.format(context.targetExtentCrs))
        ##print('NominatimFilter feedback: {}'.format(feedback))

        if len(search) < 3:
            #print('NOT searching because length: {}'.format(len(search)))
            return

        if search[-1] != ' ':
            #print('NOT searching because last char: "{}"'.format(search[-1]))
            return

        # stripping the search string here to be able to see two geocoders at once and Nominatim needs a space on the end
        #search = search.strip()
        url = 'http://nominatim.openstreetmap.org/search?format=json&q={}'.format(search)
        try:
            # TODO: Provide a valid HTTP Referer or User-Agent identifying the application (QGIS geocoder)
            # see https://operations.osmfoundation.org/policies/nominatim/
            (response, content) = self.nam.request(url)
            ##print('xx response: {}'.format(response))
            # TODO: check statuscode etc
            ##print('xx content: {}'.format(content))

            content_string = content.decode('utf-8')
            docs = json.loads(content_string)
            for doc in docs:
                #print(doc)
                result = QgsLocatorResult()
                result.filter = self
                result.displayString = '{} ({})'.format(doc['display_name'], doc['type'])
                result.userData = doc
                self.resultFetched.emit(result)

        except RequestsException:
            # Handle exception
            errno, strerror = RequestsException.args
            #print('!!!!!!!!!!! EXCEPTION !!!!!!!!!!!!!: \n{}\n{}'. format(errno, strerror))


    # /**
    #  * Triggers a filter \a result from this filter. This is called when
    #  * one of the results obtained by a call to fetchResults() is triggered
    #  * by a user. The filter subclass must implement logic here
    #  * to perform the desired operation for the search result.
    #  * E.g. a file search filter would open file associated with the triggered
    #  * result.
    #  */
    # virtual void triggerResult( const QgsLocatorResult &result ) = 0;
    def triggerResult(self, result):
        ##print('NominatimFilter triggerResult called, result: {}'.format(result))
        doc = result.userData
        extent = doc['boundingbox']
        # ?? "boundingbox": ["52.641015", "52.641115", "5.6737302", "5.6738302"]
        rect = QgsRectangle(float(extent[2]), float(extent[0]), float(extent[3]), float(extent[1]))
        dest_crs = QgsProject.instance().crs()
        results_crs = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.PostgisCrsId)
        transform = QgsCoordinateTransform(results_crs, dest_crs, QgsProject.instance())
        r = transform.transformBoundingBox(rect)
        self.iface.mapCanvas().setExtent(r, False)
        # map the result types to generic GeocoderLocator types to determine the zoom
        # BUT only if the extent < 100 meter (as for other objects it is probably ok)
        # mmm, some objects return 'type':'province', but extent is point
        scale_denominator = False  # meaning we keep the extent from the result
        #print("doc['type']: {}".format(doc['type']))
        if doc['type'] == 'house':
            scale_denominator = GeocoderLocator.ADDRESS
        elif doc['type'] in ['way', 'motorway_junction', 'cycleway']:
            scale_denominator = GeocoderLocator.STREET
        elif doc['type'] == 'postcode':
            scale_denominator = GeocoderLocator.ZIP
        if scale_denominator:
            self.iface.mapCanvas().zoomScale(scale_denominator)
        self.iface.mapCanvas().refresh()



class PdokFilter(GeocoderFilter):

    def __init__(self, nam, iface):
        super().__init__(nam, iface)
        #print('constructor PdokFilter')

    # def name(self):
    #     #print('Calling name() van PdokFilter')
    #     return 'PdokFilter'

    def clone(self):
        return PdokFilter(self.nam, self.iface)

    def displayName(self):
        ##print('Calling displayName() van PdokFilter')
        return 'PDOK Locatieserver'

    def prefix(self):
        ##print('Calling prefix() van PdokFilter')
        return 'pdok'

    # def hasConfigWidget(self):
    #     return False
    #
    # # /**
    # #  * Returns true if the filter should be used when no prefix
    # #  * is entered.
    # #  * \see setUseWithoutPrefix()
    # #  */
    # def useWithoutPrefix(self):
    #     return False

    def fetchResults(self, search, context, feedback):
        # emit resultFetched() signal
        #  /**
        #  * Retrieves the filter results for a specified search \a string. The \a context
        #  * argument encapsulates the context relating to the search (such as a map
        #  * extent to prioritize).
        #  *
        #  * Implementations of fetchResults() should emit the resultFetched()
        #  * signal whenever they encounter a matching result.
        #  *
        #  * Subclasses should periodically check the \a feedback object to determine
        #  * whether the query has been canceled. If so, the subclass should return
        #  * this method as soon as possible.
        #  */

        ##print('--- PdokFilter fetchResults called')
        ##print('PdokFilter search: {}'.format(search))
        ##print('PdokFilter context: {}'.format(context))
        #print('PdokFilter context.targetExtent: {}'.format(context.targetExtent))
        #print('PdokFilter context.targetExtentCrs: {}'.format(context.targetExtentCrs))
        ##print('PdokFilter feedback: {}'.format(feedback))

        if len(search) < 3:
            return

        # stripping the search string here to be able to see two geocoders at once and Nominatim needs a space on the end
        search = search.strip()
        url = 'https://geodata.nationaalgeoregister.nl/locatieserver/v3/suggest?q={}'.format(search)
        try:
            (response, content) = self.nam.request(url)
            ##print('response: {}'.format(response))
            # TODO: check statuscode etc
            ##print('content: {}'.format(content))

            content_string = content.decode('utf-8')
            obj = json.loads(content_string)
            docs = obj['response']['docs']
            for doc in docs:
                ##print(doc)
                result = QgsLocatorResult()
                result.filter = self
                result.displayString = '{} ({})'.format(doc['weergavenaam'], doc['type'])
                result.userData = doc
                self.resultFetched.emit(result)

        except RequestsException:
            # Handle exception
            print('!!!!!!!!!!! EXCEPTION !!!!!!!!!!!!!: \n{}'. format(RequestsException.args))


    # /**
    #  * Triggers a filter \a result from this filter. This is called when
    #  * one of the results obtained by a call to fetchResults() is triggered
    #  * by a user. The filter subclass must implement logic here
    #  * to perform the desired operation for the search result.
    #  * E.g. a file search filter would open file associated with the triggered
    #  * result.
    #  */
    # virtual void triggerResult( const QgsLocatorResult &result ) = 0;
    def triggerResult(self, result):
        #print('PdokFilter triggerResult called-----')
        ##print(result.displayString)
        ##print(result.userData)

        ##print('triggerResult called, result: {}'.format(result))

        # PDOK Location server return id's which have to picked up then
        id = result.userData['id']
        url = 'https://geodata.nationaalgeoregister.nl/locatieserver/v3/lookup?id={}'.format(id)
        try:
            (response, content) = self.nam.request(url)
            #print('response: {}'.format(response))
            # TODO: check statuscode etc
            #print('content: {}'.format(content))
            content_string = content.decode('utf-8')
            obj = json.loads(content_string)

            found = obj['response']['numFound']
            if found != 1:
                print('XXXXXXXXXXXXXXXXX  numFound != 1')
            else:
                doc = obj['response']['docs'][0]
                point = QgsPoint()
                point.fromWkt(doc['centroide_ll'])
                point_xy = QgsPointXY(point)
                dest_crs = QgsProject.instance().crs()
                results_crs = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.PostgisCrsId)
                transform = QgsCoordinateTransform(results_crs, dest_crs, QgsProject.instance())
                point_xy = transform.transform(point_xy)
                self.iface.mapCanvas().setCenter(point_xy)

                scale_denominator = 10000.0
                # map the result types to generic GeocoderLocator types to determine the zoom
                if doc['type'] == 'adres':
                    scale_denominator = GeocoderLocator.ADDRESS
                elif doc['type'] == 'weg':
                    scale_denominator = GeocoderLocator.STREET
                elif doc['type'] == 'postcode':
                    scale_denominator = GeocoderLocator.ZIP
                elif doc['type'] == 'gemeente':
                    scale_denominator = GeocoderLocator.PLACE
                elif doc['type'] == 'woonplaats':
                    scale_denominator = GeocoderLocator.CITY
                self.iface.mapCanvas().zoomScale(scale_denominator)
                self.iface.mapCanvas().refresh()

        except RequestsException:
            # Handle exception
            print('!!!!!!!!!!! EXCEPTION !!!!!!!!!!!!!: \n{}'. format(RequestsException.args))



