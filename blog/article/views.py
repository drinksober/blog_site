#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @belongto: root
# @Date:   2015-12-24 06:30:51
# @Last Modified by:   drinksober
# @Last Modified time: 2016-04-28 11:52:15

# Create your views here.
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from taggit.models import Tag
from rest_framework.views import APIView
from textrank4zh import TextRank4Keyword, TextRank4Sentence

from rest_framework.authtoken.models import Token
from .models import Article, Category, User
from .serializers import ArticleSerializer, CategorySerializer, TagSerializer


class CategoryViewSet(viewsets.ViewSet):
    def get_queryset(self):
        queryset = Category.objects.filter(status=1)
        return queryset

    def retrieve(self, request, pk):
        data = get_object_or_404(Category, pk=pk, status=1)
        data = CategorySerializer(data)
        return Response(data.data)

    def list(self, queryset):
        category_serializer = CategorySerializer(
            self.get_queryset(), many=True)
        return Response(category_serializer.data)


class TagViewSet(viewsets.ViewSet):
    def get_queryset(self):
        queryset = Tag.objects.filter()
        return queryset

    def retrieve(self, request, pk):
        data = get_object_or_404(Tag, pk=pk)
        data = TagSerializer(data)
        return Response(data.data)

    def update(self, request, pk=None):
        return self._post(request, pk)

    def create(self, request):
        return self._post(request)

    def _post(self, request, pk=None):
        name = request.GET.get('name', '')
        if not name:
            content = {'detail': '名称不能为空'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)
        tag = pk and get_object_or_404(
            Tag, pk=pk) or Tag.objects.create(name=name)
        data = TagSerializer(tag)
        return Response(data.data)

    def list(self, queryset):
        data = TagSerializer(self.get_queryset(), many=True)
        return Response(data.data)


def get_search_q_obj(request):
    search = request.GET.get('search', '')
    if not search:
        return Q()
    query_para = Q(content__contains=search) | Q(title__contains=search) | Q(
        tags__name__contains=search) | Q(category__name__contains=search)
    return query_para


class PageNumberPager(PageNumberPagination):
    def get_paginated_response(self, data):
        return Response(
            dict([('page', self.page.number), ('next', self.get_next_page()), (
                'previous', self.get_previous_page()), ('results', data)]))

    def get_previous_page(self):
        if not self.page.has_previous():
            return None
        return self.page.previous_page_number()

    def get_next_page(self):
        if not self.page.has_next():
            return None
        return self.page.next_page_number()


class ArticleViewSet(PageNumberPager, viewsets.ViewSet):
    def get_queryset(self):
        queryset = Article.objects.filter(status='1')
        return queryset

    def retrieve(self, request, pk):
        data = get_object_or_404(Article, pk=pk, status=1)
        article_serializer = ArticleSerializer(data)
        return Response(article_serializer.data)

    def list(self, request):
        query_para = get_search_q_obj(request)
        queryset = self.get_queryset().filter(query_para).distinct()
        article_serializer = ArticleSerializer(queryset, many=True)
        response = self.get_paginated_response(
            self.paginate_queryset(article_serializer.data, request))
        return response

    def update(self, request, pk=None):
        return self._operate(request, 'UPDATE', pk)

    def create(self, request):
        return self._operate(request, 'POST')

    def _operate(self, request, method, pk=None):
        user = request.user
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        background = request.FILES.get('background', '')
        return operate(user, title, content, background)


def operate(user, title, content, background=None, pk=None):
    tr4w = TextRank4Keyword()
    tr4w.analyze(text=content, lower=True, window=2)
    tags = []
    for item in tr4w.get_keywords(3, word_min_len=1):
        tag = Tag.objects.get_or_create(name=item.word)[0]
        tags.append(tag)
    category = tags and Category.objects.get_or_create(
        belongto=user, name=tags[0])[0] or ''
    tr4s = TextRank4Sentence()
    tr4s.analyze(text=content, lower=True, source='all_filters')
    summary = []
    for item in tr4s.get_key_sentences(num=3):
        summary.append(item.sentence)
    summary = ','.join(summary)
    paras = {
        'title': title,
        'summary': summary,
        'content': content,
        'category': category,
        'belongto': user
    }
    background and paras.update(background=background)
    if pk:
        article = get_object_or_404(Article, pk=pk)
        article.tags.clear()
        article.title = title
        article.summary = summary
        article.content = content
        article.category = category
    else:
        article = Article(**paras)
    article.save()
    article.tags.add(*tags)
    return Response(ArticleSerializer(article).data)


class TokenViewSet(viewsets.ViewSet):
    permission_classes = []

    def get_queryset(self):
        queryset = Token.objects.none()
        return queryset

    def list(self, request):
        if not request.user.is_authenticated():
            return Response({'detail': 'not authenticaed', 'code': '401'})
        token = Token.objects.get(user=request.user)
        return Response({'token': token})

    def create(self, request):
        if not request.user.is_authenticated():
            username = request.META.get('REMOTE_ADDR', 'visitor')
            user, ok = User.objects.get_or_create(
                username=username, role='visitor')
        else:
            user = request.user
        token, ok = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})
