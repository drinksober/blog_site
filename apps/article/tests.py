# -*- coding: utf-8 -*-
# @Author: drinks
# @Date:   2016-03-09 13:14:06
# @Last Modified by:   drinks
# @Last Modified time: 2016-03-09 17:47:22
from django.test import TestCase

from accounts.models import User
from article.models import Article, Comment, Sort
#Create your tests here.


user = User.objects.all()[0]

class ArticleMethodTest(TestCase):
    def craete(self):
        Article.objecs.create(title='test',author=user, sort=Sort.objects.get(id=1))