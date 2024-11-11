from selenium import webdriver
from time import sleep


class Scraper:

    def __init__(self):
        self.driver = webdriver.Chrome('/usr/lib/chromium-browser/chromedriver')
    
    def clean(self):
        self.driver.close()
    
    def scrape_collected(self):
        loaded = False
        trials = 3

        while not loaded:
            self.driver.get('https://henext.xyz/themadmercenary/history')
            sleep(3)
            box = self.driver.find_elements_by_class_name('ReactVirtualized__Grid__innerScrollContainer')
            if not box:
                if trials:
                    sleep(60)
                    trials = trials - 1
                else:
                    self.log_error('Collected could not be scraped. Hennext.xyz is down.')
                    return False
            else:
                loaded = True
        import pdb; pdb.set_trace()
        box = box[0]
        history = box.find_elements_by_class_name('MuiBox-root css-0')