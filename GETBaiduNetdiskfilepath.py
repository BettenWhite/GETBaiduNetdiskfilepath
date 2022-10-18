import requests
import json
from multiprocessing.pool import ThreadPool
import time
import math

class BaiDuPan(object):
    def __init__(self):
        self.session = None
        self.headers = {
            'Host': 'pan.baidu.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        }
        # 登录
        self.BDUSS=input('请输入BDUSS：')
        self.STOKEN=input('请输入STOKEN：')
        # 目标群qid
        self.qid = input('请输入qid：')
        # msg_list列表
        self.msg = []
        # 消息的展开表
        self.databack = []
        self.data = []  # 这里没有计入文件的结果
        # 求平均速度
        self.backcounter = 0
        self.counter = 0
        self.resultcounter = 0
        self.stattime = 0
        # 求瞬时速度
        self.timeslot=0
        self.responsecounter=0
        self.pool = None
        self.poolnum = 0
        # 文件总表
        self.alldic = {}

    # 设置一个客户端，之所以不在init中写是为了出现错误后能复用
    def getaclient(self):
        # 创建session并设置初始登录Cookie
        self.session = requests.session()
        self.session.cookies[
            'BDUSS'] = self.BDUSS
        self.session.cookies['STOKEN'] = self.STOKEN
        print('建立了一个客户端')

    # 设置一个的饼
    def verifyCookie(self):
        response = self.session.get(
            f'https://pan.baidu.com/mbox/homepage?action=cloudmanager&type=filefactory&gid={self.qid}',
            headers=self.headers)
        print('完成了饼的设置')

    # 得到消息列表
    def getmsgid(self):
        response = self.session.get(
            f'https://pan.baidu.com/mbox/group/listshare?gid={self.qid}&type=2',
            headers=self.headers)

        page = json.loads(response.content.decode("utf-8"))
        for i in page['records']['msg_list']:
            dic = {}
            dic['msg_id'] = i['msg_id']
            dic['uk'] = i['uk']
            dic['fs_id'] = i['file_list'][0]['fs_id']
            dic['isdir'] = i['file_list'][0]['isdir']
            self.msg.append(dic)
        self.data = self.msg
        print('完成了消息ID的获取')
        # print(self.msg)

    # 产生消息的展开
    def xstep(self, i):
        response = self.session.get(
            f'https://pan.baidu.com/mbox/msg/shareinfo?msg_id={i["msg_id"]}&from_uk={i["uk"]}&gid={self.qid}&type=2&fs_id={i["fs_id"]}',
            headers=self.headers)
        page = json.loads(response.content.decode("utf-8"))
        for j in page['records']:
            data_j = {}
            if j['isdir'] == '0' or 0:
                self.dictizeString(j['path'], 1, self.alldic)
                # print(f'进行了{j["path"]}')
            elif j['isdir'] == '1' or 1:
                data_j['msg_id'] = i["msg_id"]
                data_j['uk'] = i['uk']
                data_j['fs_id'] = j['fs_id']
                data_j['isdir'] = j['isdir']
                data_j['path'] = j['path']
                self.data.append(data_j)
                self.counter += 1
        response.close()
        self.databack.remove(i)
        self.backcounter -= 1
        self.responsecounter += 1
        if self.responsecounter != 1 and self.responsecounter % 300 == 1:
            print("\r当前瞬时响应速度{:.3f}条每秒，池中还有{}条待处理，下一方池子将处理{}条，已获得路径{}个".format(300/(time.time()-self.timeslot+0.001),
                                                                                                self.backcounter,self.counter,
                                                                                                self.resultcounter),end='')
            self.timeslot=float(time.time())

    # 挡位调节
    def gear(self, num):
        a = [2, 4, 8, 16, 32, 64, 128, 256]  # 挡位
        # a = [2, 4, 8, 16, 128]  # 挡位 测试用
        b = math.pow(2,math.log10(num / 5)*8/5)
        return min(a, key=lambda x: abs(x - b))

    # 获得一个线程池
    def setapool(self, data, num):
        self.poolnum += 1
        self.databack = self.data
        self.data = []
        self.backcounter = self.counter
        self.counter = 0
        print('\n清理了data')
        print(f'开始第{self.poolnum}个池子，设置{num}的池子')
        self.pool = ThreadPool(num)  # 线程数
        print(f'设置成功了{num}的池子')
        self.pool.map(self.xstep, data)  # 多线程工作
        self.pool.close()
        self.pool.terminate()  # 结束工作进程，不再处理未处理的任务。
        self.pool.join()

    # 数据处理
    def dictizeString(self, string, value, dictionary):
        while string.startswith('/'):
            string = string[1:]
        parts = string.split('/', 1)
        if len(parts) > 1:
            branch = dictionary.setdefault(parts[0], {})  # 如果字典中包含有给定键，则返回该键对应的值，否则返回为该键设置的值。
            self.dictizeString(parts[1], value, branch)
        else:
            if parts[0] in dictionary:
                dictionary[parts[0]] += 1
            else:
                dictionary[parts[0]] = value
        self.resultcounter += 1

    # 错误处理
    def errdeal(self):
        self.pool.close()  # 测试一下，可以详细了解一下这部分函数的用法
        self.pool.terminate()  # 结束工作进程，不再处理未处理的任务。
        self.pool.join()  # 测试一下，可以详细了解一下这部分函数的用法
        self.data = self.databack + self.data
        self.counter = self.counter + self.backcounter
        # self.counter=10  # 测试用
        self.databack = []
        self.backcounter = 0
        time.sleep(10)
        print('\n出错了，10秒后重试')
        self.session.close()
        print('旧的客户端关闭')
        self.getaclient()
        print('新的客户端建立')
        self.verifyCookie()

    # 转文本模块
    def dic2txt(self,text, f, prefix='\t'):
        for i in text.keys():
            if isinstance(text[i], dict):
                f.write(prefix + '+ ' + i + '\n')
                self.dic2txt(text[i], f, prefix + '|   ')  # 最后一个└
            else:
                f.write(prefix + '- ' + i + '\n')



def main():
    # 实例一个客户端
    record = BaiDuPan()
    record.getaclient()
    # 设置登录饼干
    record.verifyCookie()
    # 获得消息列表
    record.getmsgid()
    # 第一次展开
    record.setapool(record.msg, record.gear(len(record.msg)))

    # 设置线程池
    while record.data:
        try:
            record.setapool([x for x in record.data], record.gear(record.counter))
        except:
            record.errdeal()

    # f = open("record.json", "w")
    # json.dump(record.alldic, f)
    # f.close()
    print('进行数据整合')
    with open('record.txt', 'w', encoding='utf-8') as fi:
        record.dic2txt(record.alldic, fi)


if __name__ == "__main__":
    main()
