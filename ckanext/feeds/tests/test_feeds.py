# encoding: utf-8
'''
Tests for the ckanext-feeds extension.
'''

import paste.fixture
import pylons.test
import pylons.config as config
import webtest

from nose.tools import assert_raises, assert_equal

import ckan.model as model
import ckan.tests.legacy as tests
import ckan.plugins
import ckan.tests.factories as factories
import ckan.logic as logic



class TestFeeds(object):
    '''Tests for the ckanext.feeds.plugin module.'''

    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''

        # Make the Paste TestApp that we'll use to simulate HTTP requests to
        # CKAN.
        # cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)

        # load plugin to be tested
        ckan.plugins.load('feeds')

    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''
        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        '''Nose runs this method once after all the test methods in our class have been run.
        '''
        # unload the plugin, so it doesn't affect any tests that run after this one
        ckan.plugins.unload('feeds')



    def _get_app(self):
        # Return a test app with the custom config.
        app = ckan.config.middleware.make_app(config['global_conf'], **config)
        app = webtest.TestApp(app)

        ckan.plugins.load('feeds')

        return app


    def test_mimetype_is_rss_when_requesting_rss_feed(self):
        app = self._get_app()
        # user = factories.User()
        resp = app.get('/dashboard?format=rss')
        assert resp.content_type == 'application/rss+xml'
        resp = app.get('/dashboard?format=rss&version=2.01')
        assert resp.content_type == 'application/rss+xml'
        resp = app.get('/dashboard?format=rss&version=0.91')
        assert resp.content_type == 'application/rss+xml'

    def test_mimetype_is_atom_when_requesting_atom_feed(self):
        app = self._get_app()
        # user = factories.User()
        resp = app.get('/dashboard?format=atom')
        assert resp.content_type == 'application/atom+xml'
