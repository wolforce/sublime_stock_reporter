#coding=utf-8
import sublime, sublime_plugin
import threading
import re

try:
    import urllib2
    from xpinyin import Pinyin
    isPython2 = True
except ImportError:
    import urllib.request as urllib2
    isPython2 = False

status_key = "StockInfo"

class StockrepoterCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings("Preferences.sublime-settings")
        stocks   = settings.get("stocks")
        thread   = FetchStocksCall(stocks)
        thread.start()
        self.edit = edit
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
        sh = ['001', '110', '120', '129', '100', '201', '310', '500', '510', '550', '6', '700', '710', '701', '711', '720', '730', '735', '737', '900']
        prefix = 'sz'
        for num in sh:
            if no.startswith('sh') or no.startswith('sz'):
                prefix = ''
                break
            elif no.startswith(num):
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

    #因为sublime2不支持在状态栏显示中文，所以在python2下用拼音表示股票名，在python3下直接使用中文.
    def get_stock_name(self, name, show_pinyin):
        stockName = ""
        if isPython2 or show_pinyin:
            stockName = Pinyin().get_initials(self.strQ2B(name), u'')
        else:
            stockName = name
        return stockName

    def run(self):
        try:
            show_pinyin = False
            show_price = False
            noList = []
            for stock in self.stocks:
                no = stock.get('no')
                if no:
                    noList.append(self.get_stock_with_prefix(no))
                else:
                    show_pinyin = stock.get('show_pinyin')
                    show_price = stock.get('show_price')

            request  = urllib2.Request('http://hq.sinajs.cn/list=' + ','.join(noList))
            response = urllib2.urlopen(request)
            result   = response.read().decode('gbk')
            lines    = result.strip().split('\n')
            for line in lines:
                text           = re.sub('var.+=[^"]*"', '', line)
                infos          = text.split(',')
                stockName      = self.get_stock_name(infos[0], show_pinyin)
                yesterdayPrice = float(infos[2])
                curPrice       = float(infos[3])
                percent        = (curPrice / yesterdayPrice - 1) * 100
                if show_price:
                    percentStr = str(curPrice) + "(" + str('%0.2f'%percent) + '%)'
                else:
                    percentStr = str('%0.2f'%percent) + '%'
                self.priceList.append({'name':stockName, 'percent': percentStr})
            return
        except urllib2.HTTPError:
            err = '%s: HTTP error %s contacting API' % (__name__, str(urllib2.HTTPError.code))
        except urllib2.URLError:
            err = '%s: URL error %s contacting API' % (__name__, str(urllib2.URLError.reason))

        sublime.error_message(err)
