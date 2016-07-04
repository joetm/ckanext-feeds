# encoding: utf-8
'''
Tests for the ckanext-feeds extension.
'''

import paste.fixture
import pylons.test
import pylons.config as config
import ckan.config
import webtest

import ckan.model as model
import ckan.tests.legacy as tests
import ckan.tests.helpers as h
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.logic as logic

# webtest_submit = h.webtest_submit
# submit_and_follow = h.submit_and_follow

from nose.tools import assert_raises, assert_equal, raises, nottest, istest


class TestFeeds(object):

    '''Tests for the ckanext.feeds.plugin module.'''

    @classmethod
    def setup_class(self):
        '''Nose runs this method once to setup our test class.'''

        # Make the Paste TestApp that we'll use to simulate HTTP requests to CKAN.
        self.ckan_app = paste.fixture.TestApp(pylons.test.pylonsapp)

        app = ckan.config.middleware.make_app(config['global_conf'], **config)
        self.app = webtest.TestApp(app)

        # load plugin to be tested
        if not p.plugin_loaded('feeds'):
            p.load('feeds')

    def setup(self):
        '''Nose runs this method before each test method in our test class.'''
        pass

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
        if p.plugin_loaded('feeds'):
            p.unload('feeds')


    @istest
    def test_get_dashboard_user_not_loggedin(self):
        url = h.url_for(controller='dashboard_feed', action='view_dashboard_feed')
        resp = self.app.get(url)
        assert resp.status == '302 Found'
        assert resp.status_int == 302
        assert '/user/login' in resp.location # 'http://localhost/user/login'


    @istest
    def test_get_dashboard_user_loggedin(self):

        user = factories.User()
        owner_org = factories.Organization(users=[{'name': user['id'], 'capacity': 'admin'}])
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])

        # resp = tests.call_action_api(app, 'dashboard_feed', name='test-dashboard')
        resp = self.app.get('/dashboard?format=rss')

        assert resp.status_int == 200
        assert resp.content_length > 0


