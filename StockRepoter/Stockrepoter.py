#coding=utf-8
import sublime, sublime_plugin
import urllib2
import threading
import re
from xpinyin import Pinyin

status_key = "StockInfo"

class StockrepoterCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings("Preferences.sublime-settings")
        stocks   = settings.get("stocks")
        thread   = FetchStocksCall(stocks)
        thread.start()
        self.handle_thread(thread)

    def handle_thread(self, thread):
        if thread.is_alive():
            sublime.set_timeout(lambda: self.handle_thread(thread), 100)
            return

        outList = []
        for price in thread.priceList:
            outList.append(price.get('name') + " => " + price.get('percent'))
        self.view.set_status(status_key, '        '.join(outList) + '        ')
        

class StockrepotercleanCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.set_status(status_key, "")




class FetchStocksCall(threading.Thread):
    def __init__(self, stocks):
        self.stocks    = stocks
        self.priceList = []
        threading.Thread.__init__(self)

    def get_stock_with_prefix(self, no):
        sh = [001, 110, 120, 129, 100, 201, 310, 500, 550, 600, 700, 710, 701, 711, 720, 730, 735, 737, 900]
        prefix = 'sz'
        for num in sh:
            if no.startswith(str(num)):
                prefix = 'sh'
                break
        return prefix + no

    #全角转半角
    def strQ2B(self, ustring):
        rstring = ""
        for uchar in ustring:
            inside_code=ord(uchar)
            if inside_code == 12288:                              #全角空格直接转换            
                inside_code = 32 
            elif (inside_code >= 65281 and inside_code <= 65374): #全角字符（除空格）根据关系转化
                inside_code -= 65248
            rstring += unichr(inside_code)
        return rstring

    def run(self):
        try:
            p = Pinyin()
            for stock in self.stocks:
                no       = stock.get('no')
                request  = urllib2.Request('http://hq.sinajs.cn/list=' + self.get_stock_with_prefix(no))
                response = urllib2.urlopen(request)
                result   = response.read().decode('gbk')
                text     = re.sub('var.+=[^"]*"', '', result)
                infos    = text.split(',')
                stockName      = p.get_initials(self.strQ2B(infos[0]), u'')
                yesterdayPrice = float(infos[2])
                curPrice       = float(infos[3])
                percent        = (curPrice / yesterdayPrice - 1) * 100,
                percentStr     = str('%0.2f'%percent) + "%"
                self.priceList.append({'no':no, 'name':stockName, 'percent': percentStr})
            return
        except (urllib2.HTTPError) as (e):
            err = '%s: HTTP error %s contacting API' % (__name__, str(e.code))
        except (urllib2.URLError) as (e):
            err = '%s: URL error %s contacting API' % (__name__, str(e.reason))

        sublime.error_message(err)
