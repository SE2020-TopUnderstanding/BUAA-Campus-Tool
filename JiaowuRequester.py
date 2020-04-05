#-*-coding: UTF-8 -*-
import time

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


JIAOWU_VPN_URL = "https://e2.buaa.edu.cn/users/sign_in"
USERNAME = "统一认证用户名"
PASSWORD = "统一认证密码"

class JiaowuRequester:
    """
    教务爬虫的简单轮子，使用selenium作为核心支持库制作，和制作抢课脚本是一个思路（首先声明我没做过）。
    因为教务的登录行为较为麻烦，不能够用传统的爬虫方式发送请求来爬取，所以使用无头浏览器。
    """

    def __init__(self, username, password):
        """
        初始化webdriver。
        设置chrome的headless模式，从而在没有图形界面的服务器上也可以使用。
        """
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36")
        self.b = webdriver.Chrome(chrome_options=options)
        self.code = self.login_vpn(username, password)

    def login_vpn(self, username, password):
        """
        通过VPN登录教务系统。
        由于服务器部署在校外，所以需要借助VPN来登录。
        VPN密码输入若超过五次，则账号会被暂时锁定。需要等待一个小时后重试。
        成功后，将页面引导至教务系统主页。
        """
        self.b.get(JIAOWU_VPN_URL)
        input_username = self.b.find_element_by_id("user_login")
        input_password = self.b.find_element_by_id("user_password")
        input_username.send_keys(username)
        input_password.send_keys(password)
        self.b.find_elements_by_name("commit")[0].click()
        try:
            WebDriverWait(self.b, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//a[@data-original-title]')))
        except Exception:
            if self.b.current_url == JIAOWU_VPN_URL:
                # 登录失败，需要找寻原因
                error_text = self.b.find_element_by_xpath('//*[@id="canvas"]/div[2]/div[2]/div[1]').text.split("\n")[1]
                print(error_text)
            else:
                print("超时或跳转到未知页面！")
            return -1
        self.b.find_elements_by_xpath('//a[@data-original-title="教务管理系统"]')[0].click()
        #time.sleep(1)
        # 将页面切换到教务系统页面
        all_handles = self.b.window_handles
        for handles in all_handles:
            if self.b.current_window_handle != handles:
                self.b.switch_to_window(handles)
        try:
            WebDriverWait(self.b, 5, 0.5).until(EC.presence_of_element_located((By.ID, 'navList')))
        except Exception:
            print("页面加载超时！")
            return -2
        print(self.b.current_url)
        return 0

    def get_grade(self, value):
        """
        获取学生成绩
        参数value的意义是指定查询哪个学年的成绩，从1开始编号。
        1代表大一上学期，2代表大一下学期，3代表大一暑假，以此类推。
        返回值是指定学期下所有学科的成绩列表，按照教务网站上的信息列出。
        """
        # 这个按钮无法用寻常的click手段点击，所以调用js脚本强制执行
        element = self.b.find_element_by_xpath('//a[@href="/ieas2.1/cjcx/queryCjpub_ty"]')
        self.b.execute_script("arguments[0].click();", element)
        # 教务使用了内嵌的iframe，我们要切到iframe内部查看其信息
        self.b.switch_to.frame("iframename")
        try:
            WebDriverWait(self.b, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//a[@class="qmcx"]')))
        except Exception:
            print("页面加载超时！")
            return [-1]
        self.b.find_element_by_xpath('//a[@class="qmcx"]').click()
        try:
            WebDriverWait(self.b, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="xnxqid"]')))
        except Exception:
            print("页面加载超时或者输入的时间错误！")
            return [-2]
        self.b.find_element_by_xpath('//*[@id="xnxqid"]/option[' + str(value - 1) + ']').click()
        self.b.find_element_by_xpath('//div[@class="addlist_button2"]/a').click()
        # 让成绩加载一秒钟
        time.sleep(1)
        table = self.b.find_element_by_xpath("//body/div[1]/div/div[4]/table/tbody")
        rows = table.find_elements_by_tag_name("tr")
        rows.pop(0)
        grades = []
        for tr in rows:
            grade = []
            tds = tr.find_elements(By.TAG_NAME, "td")
            for td in tds:
                grade.append(td.text)
            grades.append(grade)
        return grades

    def get_course_schedule(self, value=0):
        """
        获取学期课表
        参数value的意义是制定获取某一周的课表，周数需要在本学期存在的周范围内。
        若value等于0或不输入，则代表获取整个学期的课表。
        返回值是列表，以教务网站上的课表格式列出。
        """
        # 这个按钮无法用寻常的click手段点击，所以调用js脚本强制执行
        element = self.b.find_element_by_xpath('//a[@href="/ieas2.1/kbcx/queryGrkb"]')
        self.b.execute_script("arguments[0].click();", element)
        # 教务使用了内嵌的iframe，我们要切到iframe内部查看其信息
        self.b.switch_to.frame("iframename")
        try:
            WebDriverWait(self.b, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//div[@class="xfyq_con"]')))
        except Exception:
            print("页面加载超时！")
            return [-1]

        if value == 0:
            schedule_top = self.b.find_element_by_xpath('//div[@class="xfyq_top"]/span').text
            print(schedule_top)
            table = self.b.find_element_by_xpath("//body/div[1]/div/div[8]/div[2]/table/tbody")
        else:
            self.b.find_element_by_xpath("//body/div[1]/div/div[6]/ul/li[2]/a").click()
            try:
                WebDriverWait(self.b, 5, 0.5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="zc"]')))
            except Exception:
                print("页面加载超时！")
                return [-1]
            self.b.find_element_by_xpath('//*[@id="zc"]/option[' + str(value) + ']').click()
            self.b.find_element_by_xpath('//*[@id="queryform"]/table/tbody/tr/td[5]/div').click()
            # 让其加载一秒
            time.sleep(1)
            table = self.b.find_element_by_xpath('//body/div/div/div[7]/div[2]/table/tbody')
        
        rows = table.find_elements_by_tag_name("tr")
        rows.pop(0)
        courses = []
        for tr in rows:
            course = []
            tds = tr.find_elements(By.TAG_NAME, "td")
            for td in tds:
                course.append(td.text)
            courses.append(course)
        return courses

if __name__ == "__main__":
    spider = JiaowuRequester(USERNAME, PASSWORD)
    print(spider.get_grade(2))
    print(spider.get_course_schedule(10))
    