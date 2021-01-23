# -*- coding: utf-8 -*-
'''original version from https://github.com/ZihaoZhao/Arxiv_daily,
adjusted by zhenzhiwang to be https://github.com/zhenzhiwang/daily_arxiv'''

import requests
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
import pymysql
from collections import Counter
import os
import random

import smtplib
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


def get_one_page(url):
    response = requests.get(url)
    print('reponse from url =',response.status_code)
    while response.status_code == 403:
        time.sleep(500 + random.uniform(0, 500))
        response = requests.get(url)
        print(response.status_code)
    print('reponse from url =', response.status_code)
    if response.status_code == 200:
        return response.text
    return None


def send_email(receiver, title, content):

    # sender's email address
    sender = ''
    # sender's email username and password
    user = ''

    # 需要在邮箱账户里开启任意客户端登录的功能，此密码与邮箱密码不同，一般是一串大写字母; 
    # this password is different from the one we set, we need to turn on accesses from any devices in the email account
    # and get the special password provided from the email account (ususally they are strings of capitialized characters) 
    password = ''  
    # smtp server address
    smtpserver = ''  # e.g., smtp.163.com for 163.com
    
    msg = MIMEMultipart('alternative')  
    part1 = MIMEText(content, 'plain', 'utf-8')  
    msg.attach(part1)  

    #sender's email address
    msg['From'] = sender
    #receiver's email address
    msg['To'] = receiver
    #title
    msg['Subject'] = title

    smtp = smtplib.SMTP() 
    smtp.connect(smtpserver, 25) # default port is 25
    smtp.login(user, password) # login smtp server
    smtp.sendmail(sender, receiver, msg.as_string()) #send emails
    smtp.quit()


def main():
    '''content to be filled: (1) key-words/not-interested-key-words (ignore/keep cases), (2) local directory to save files, 
        (3) email sender (account/password), (4) email receiver, (5) smtpserver'''
    
    '''Set personalized values'''
    # subjects
    subjects_of_interest = ['cs.CV']  # domains to select
    not_interested_subjects = ['cs.RO'] # domains to be removed
    # keywords, any paper title containing such strings are selected for paper-lists in emails
    key_words = [' action detection']  # key words which ignore cases, we recommand to include ' ' around words to avoid unexpected results, e.g., 'interaction detection' result searched by 'action detection' keywords
    Key_words = []  # key words which keep captialization
    # keywords to remove papers containing such strings
    not_interested_words = ['robot', 'point cloud']  # any paper title containing such strings are removed, where stings ignore cases
    Not_interested_words = ['RGB-D']  # any paper title containing such strings are removed, where strings keep cases
    # local directory for saving papers/ csv files/ email contenet txt files
    local_dir=''
    # the webpage url to do search
    url = 'https://arxiv.org/list/cs/pastweek?show=2000'
    #url = 'https://arxiv.org/list/cs.CV/2012?show=2000'  # to search previous papers, such as Dec 2020 in cs.CV domain
    #url = 'https://arxiv.org/list/cs/2101?skip=2000&show=2000'
    
    # email receiver
    receiver = '' # we recommand to send emails to ourselves, otherwise the emails may be classifies as spam emails
    has_statistics = False  # whether email containing statistics of sub-domains (such as cs.CV) in cs
    download_pdf = True  # whether downloading pdfs
    has_last_authors = True  # whether including corresponding author (the last one) in the email content
    

    '''Codes start from here'''
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    if not os.path.exists(local_dir + 'csv_file/'):
        os.makedirs(local_dir + 'csv_file/')
    if not os.path.exists(local_dir + 'pdf/'):
        os.makedirs(local_dir + 'pdf/')
    html = get_one_page(url)
    soup = BeautifulSoup(html, features='html.parser')
    content = soup.dl
    date = soup.find('h3')
    list_ids = content.find_all('a', title = 'Abstract')
    list_title = content.find_all('div', class_ = 'list-title mathjax')
    list_authors = content.find_all('div', class_ = 'list-authors')
    list_subjects = content.find_all('div', class_ = 'list-subjects')
    list_subject_split = []
    for subjects in list_subjects:
        subjects = subjects.text.split(': ', maxsplit=1)[1]
        subjects = subjects.replace('\n\n', '')
        subjects = subjects.replace('\n', '')
        subject_split = subjects.split('; ')
        list_subject_split.append(subject_split)

    items = []
    for i, paper in enumerate(zip(list_ids, list_title, list_authors, list_subjects, list_subject_split)):
        items.append([paper[0].text, paper[1].text, paper[2].text, paper[3].text, paper[4]])
    name = ['id', 'title', 'authors', 'subjects', 'subject_split']
    paper = pd.DataFrame(columns=name,data=items)
    paper.to_csv(local_dir+'csv_file/'+time.strftime("%Y-%m-%d")+'_'+str(len(items))+'.csv')
    print("Webpage has been downloaded, start paper selecting.")
    
    '''subject split'''
    subject_all = []
    for subject_split in list_subject_split:
        for subject in subject_split:
            subject_all.append(subject)
    subject_cnt = Counter(subject_all)
    #print(subject_cnt)
    subject_items = []
    for subject_name, times in subject_cnt.items():
        subject_items.append([subject_name, times])
    subject_items = sorted(subject_items, key=lambda subject_items: subject_items[1], reverse=True)
    name = ['name', 'times']
    subject_file = pd.DataFrame(columns=name,data=subject_items)
    #subject_file = pd.DataFrame.from_dict(subject_cnt, orient='index')
    subject_file.to_csv(local_dir+'csv_file/'+time.strftime("%Y-%m-%d")+'_'+str(len(items))+'.csv')
    #subject_file.to_html('subject_file.html')    
    
    '''select subjects of interest'''
    subject_papers=paper[paper['subjects'].str.contains(subjects_of_interest[0], case=False)]
    for selected_subject in subjects_of_interest[1:]:
        temp=paper[paper['subjects'].str.contains(selected_subject, case=False)]
        subject_papers=pd.concat([subject_papers, temp], axis=0)
    
    #print(subject_papers)
    subject_papers = subject_papers.drop_duplicates(subset=['id'])
    for subject in not_interested_subjects:
        subject_papers= subject_papers.drop(subject_papers[subject_papers['subjects'].str.contains(subject, case=False)].index)
    
    '''key_word selection'''
    selected_papers = subject_papers[subject_papers['title'].str.contains(key_words[0], case=False)]
    for key_word in key_words[1:]:
        selected_paper1 = subject_papers[subject_papers['title'].str.contains(key_word, case=False)]
        selected_papers = pd.concat([selected_papers, selected_paper1], axis=0)
    for Key_word in Key_words[1:]:
        selected_paper1 = subject_papers[subject_papers['title'].str.contains(Key_word, case=True)]
        selected_papers = pd.concat([selected_papers, selected_paper1], axis=0)
    for word in not_interested_words:
        selected_papers= selected_papers.drop(selected_papers[selected_papers['title'].str.contains(word, case=False)].index)
    for Word in Not_interested_words:
        selected_papers= selected_papers.drop(selected_papers[selected_papers['title'].str.contains(Word, case=True)].index)
    selected_papers = selected_papers.drop_duplicates(subset=['id'])
    selected_papers.to_csv(local_dir+'csv_file/'+time.strftime("%Y-%m-%d")+'_'+str(len(selected_papers))+'.csv')


    '''send email'''
    #selected_papers.to_html('email.html')
    content = 'Today has {} new papers in CS area, and {} of them are about CV, where {} contain your keywords.\n\n'.format(len(list_title), subject_cnt['Computer Vision and Pattern Recognition (cs.CV)'], len(selected_papers))
    content += 'Your current keywords is ' + str(key_words) + ' and ' + str(Key_words) + '(case=True). \n\n'
    content += 'Your paperlist is as follows. Please Enjoy! \n\n'
    for i, (id, title, authors, subject) in enumerate(zip(selected_papers['id'], selected_papers['title'], selected_papers['authors'], selected_papers['subject_split'])):
        #print(content1)
        title = title.split(':', maxsplit=1)[1]
        content += '------------' + str(i+1) + '------------\n' + id + title
        if has_last_authors:
            content += authors.split('\n')[-2] + '\n'
        content += str(subject) + '\n'
        id = id.split(':', maxsplit=1)[1]
        content += 'https://arxiv.org/abs/' + id + '\n\n'
    content += 'The end of paperlist. \n\n'
    
    if has_statistics:
        content += 'Here is the Research Direction Distribution Report. \n\n'
        for subject_name, times in subject_items:
            content += subject_name + '   ' + str(times) +'\n'
        
    title = time.strftime("%Y-%m-%d") + ' you have {} papers'.format(len(selected_papers))
    freport = open(local_dir+title+'.txt', 'w')
    freport.write(content)
    freport.close()
    print('Content has been saved to text file: %s.txt.'% title)
    send_email(receiver, title, content)
    print('Email has been sent to %s.'%receiver)
    
    '''download key_word selected papers'''
    if download_pdf:
        list_subject_split = []
        if not os.path.exists(local_dir+'pdf/'+time.strftime("%Y-%m-%d")):
            os.makedirs(local_dir+'pdf/'+time.strftime("%Y-%m-%d"))
        for selected_paper_id, selected_paper_title in zip(selected_papers['id'], selected_papers['title']):
            selected_paper_id = selected_paper_id.split(':', maxsplit=1)[1]
            selected_paper_title = selected_paper_title.split(':', maxsplit=1)[1]
            r = requests.get('https://arxiv.org/pdf/' + selected_paper_id)
            while r.status_code == 403:
                time.sleep(500 + random.uniform(0, 500))
                r = requests.get('https://arxiv.org/pdf/' + selected_paper_id)
            selected_paper_id = selected_paper_id.replace(".", "_")
            pdfname = selected_paper_title.replace("/", "_")   #pdf file name can not contain /, :
            pdfname = pdfname.replace("?", "_")
            pdfname = pdfname.replace("\"", "_")
            pdfname = pdfname.replace("*","_")
            pdfname = pdfname.replace(":","_")
            pdfname = pdfname.replace("\n","")
            pdfname = pdfname.replace("\r","")
            print(local_dir+time.strftime("%Y-%m-%d")+'/%s %s.pdf' %(selected_paper_id, pdfname))
            with open(local_dir+'pdf/'+time.strftime("%Y-%m-%d")+'/%s.pdf'%(pdfname), "wb") as code:
               code.write(r.content)

if __name__ == '__main__':
    main()
    time.sleep(1)




