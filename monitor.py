from discord import Webhook, RequestsWebhookAdapter, Embed
from proxymanager import ProxyManager
import pprint
import requests
import sys
import time
import ujson


requests.models.json = ujson


# noinspection PyPep8Naming,PyPep8Naming,PyPep8Naming,PyPep8Naming,PyPep8Naming,PyPep8Naming,PyPep8Naming,PyPep8Naming
class NikeSNKRSMonitor(object):

    def __init__(self):
        self.apiLink = "https://api.nike.com/product_feed/threads/v2/?anchor=0&count=50&filter=marketplace%28US%29&filter=language%28en%29&filter=channelId%28010794e5-35fe-4e32-aaff-cd2c74f89d61%29&filter=exclusiveAccess%28false%29"
        self.productApiLink = f'https://api.nike.com/product_feed/threads/v2/?filter=marketplace%28US%29&filter=language%28en%29&filter=channelId%28010794e5-35fe-4e32-aaff-cd2c74f89d61%29&filter=seoSlugs%28'
        self.mostRecent = []
        self.webhookURL = 'https://discordapp.com/api/webhooks/695493120028311552/ToN3xya822ZAnZdn2dmi7eozPUkCCj8wz1aPxKocvaSVcV6syv8T1qeLtRKI8xYtyKjf'
        self.webhook = Webhook.from_url(self.webhookURL, adapter=RequestsWebhookAdapter())

    def _skuToStockLevel(self, skuList):
        result = {}
        for skuDict in skuList:
            result[skuDict['id']] = skuDict['level']
        return result

    def _getAvailability(self, skuList, skuToStockLevel):
        result = ''
        for skuDetails in skuList:
            size = skuDetails['countrySpecifications'][0]['localizedSize']
            stockLevel = skuToStockLevel[skuDetails['id']]
            result += f'{size}({stockLevel})\n'
        return result

    def _createEmbed(self, slug, title, imgURL, price, currency, sizes, method, releaseDate):
        e = Embed()
        e.title = title
        e.description = f'https://www.nike.com/launch/t/{slug}'
        e.set_thumbnail(url=imgURL)
        e.set_footer(text='Nike US SNKRS Monitor powered by iPandaFNF', icon_url='https://pbs.twimg.com/profile_images/1113987305268817920/IvjFqsFi_400x400.png')
        e.add_field(name='Price', value=f'{price}{currency}')
        e.add_field(name='Method', value=method)
        e.add_field(name='Release Date', value=releaseDate)
        e.add_field(name='Availability', value=sizes)
        return e

    def _getProduct(self, slug):
        subRequestURL = self.productApiLink + f'{slug}%29'
        subR = requests.get(subRequestURL)
        return subR.json()['objects'][0]

    def _getProductInfo(self, product):
        if product.get('productInfo'):
            price = product['productInfo'][0]['merchPrice']['fullPrice']
            currency = product['productInfo'][0]['merchPrice']['currency']
            skuToStockLevel = self._skuToStockLevel(product['productInfo'][0]['availableSkus'])
            sizes = self._getAvailability(product['productInfo'][0]['skus'], skuToStockLevel)
            method = product['productInfo'][0]['launchView']['method']
            releaseDate = product['productInfo'][0]['launchView']['startEntryDate'].split('T')[0]
        else:
            price = None
            currency = None
            sizes = None
            method = None
            releaseDate = None
        return price, currency, sizes, method, releaseDate

    def _parseProperties(self, obj):
        slug = obj['publishedContent']['properties']['seo']['slug']
        title = obj['publishedContent']['properties']['seo']['title']
        imgURL = obj['publishedContent']['properties']['coverCard']['properties']['portraitURL']
        return slug, title, imgURL

    def getTopNProducts(self, n=1):
        r = requests.get(self.apiLink)
        jsonObj = r.json()
        objects = jsonObj['objects']
        count = 0
        for obj in objects:
            slug, title, imgURL = self._parseProperties(obj)
            product = self._getProduct(slug)
            price, currency, sizes, method, releaseDate = self._getProductInfo(product)
            self.webhook.send(embed=self._createEmbed(slug, title, imgURL, price, currency, sizes, method, releaseDate))
            count += 1
            if count >= n:
                break

    def monitor(self, sleepTime=30):
        proxyManager = ProxyManager('proxies.txt')
        self._productsSeen = []
        self.getTopNProducts(1) # publish the latest product seen at the start of the monitoring
        r = requests.get(self.apiLink)
        jsonObj = r.json()
        objects = jsonObj['objects']
        for obj in objects:
            slug, title, imgURL = self._parseProperties(obj)
            self._productsSeen.append(title)
        while(True):
            print('Looking for products')
            proxy = proxyManager.random_proxy()
            r = requests.get(self.apiLink, proxies=proxy.get_dict())
            jsonObj = r.json()
            objects = jsonObj['objects']
            for obj in objects:
                slug, title, imgURL = self._parseProperties(obj)
                if title in self._productsSeen:
                    continue
                self._productsSeen.append(title)
                product = self._getProduct(slug)
                price, currency, sizes, method, releaseDate = self._getProductInfo(product)
                self.webhook.send(
                    embed=self._createEmbed(slug, title, imgURL, price, currency, sizes, method, releaseDate))
                print('Found new product!')
            print('Sleeping for %ss, will query for products once done'%sleepTime)
            time.sleep(sleepTime)

if __name__ == '__main__':
    m = NikeSNKRSMonitor()
    if len(sys.argv) == 1:
        m.monitor()
    else:
        sleepTime = sys.argv[1]
        m.monitor(sleepTime)
