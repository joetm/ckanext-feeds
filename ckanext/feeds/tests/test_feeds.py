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
import ckan.tests.helpers as testhelpers
import ckan.lib.helpers as helpers
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.logic as logic

# webtest_submit = testhelpers.webtest_submit
# submit_and_follow = testhelpers.submit_and_follow

from nose.tools import assert_raises, assert_equal, raises, nottest, istest


class TestFeeds(object):

    '''Tests for the ckanext.feeds.plugin module.'''

    @classmethod
    def setup_class(self):
        '''Nose runs this method once to setup our test class.'''

        # Make the Paste TestApp that we'll use to simulate HTTP requests to CKAN.
        # self.ckan_app = paste.fixture.TestApp(pylons.test.pylonsapp)

        application = ckan.config.middleware.make_app(config['global_conf'], **config)
        self.webtest_app = webtest.TestApp(application)

        # load plugin to be tested
        if not p.plugin_loaded('feeds'):
            p.load('feeds')

    def setup(self):
        '''Nose runs this method before each test method in our test class.'''
        self.url = 'http://localhost' + helpers.url_for('/dashboard')

        self.user = factories.User()
        self.owner_org = factories.Organization(users=[{'name': self.user['id'], 'capacity': 'admin'}])
        self.dataset = factories.Dataset(owner_org=self.owner_org['id'])
        self.resource = factories.Resource(package_id=self.dataset['id'])

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
        # the default answer by CKAN is 'resource not found' (with status 404)
        resp = self.webtest_app.get(self.url, status=404, expect_errors=True)
        assert resp.status == '404 Not Found'
        assert resp.status_int == 404

    @istest
    def test_get_rss_dashboard_user_not_loggedin(self):
        resp = self.webtest_app.get(self.url, params='format=rss', status=302, expect_errors=True)
        assert resp.status == '302 Found'
        assert resp.status_int == 302
        assert '/user/login' in resp.location # 'http://localhost/user/login'

    @istest
    def test_get_atom_dashboard_user_not_loggedin(self):
        resp = self.webtest_app.get(self.url, params='format=atom', status=302, expect_errors=True)
        assert resp.status == '302 Found'
        assert resp.status_int == 302
        assert '/user/login' in resp.location # 'http://localhost/user/login'

    @istest
    def test_get_normal_dashboard_user_loggedin(self):

        env = {'REMOTE_USER': self.user['name'].encode('ascii')}

        # resp = tests.call_action_api(app, 'dashboard_feed', name='test-dashboard')

        resp = self.webtest_app.get(url=self.url, status=200, expect_errors=False, extra_environ=env)

        assert_equal(resp.status_int, 200)
        assert resp.content_length > 0

    @istest
    def test_get_rss_feed_user_loggedin(self):

        env = {'REMOTE_USER': self.user['name'].encode('ascii')}

        resp = self.webtest_app.get(url=self.url, params='format=rss', status=200, expect_errors=False, extra_environ=env)

        assert_equal(resp.status_int, 200)
        assert resp.content_length > 0
        resp.mustcontain('<?xml')
        assert_equal(resp.header('Content-Type'), 'application/rss+xml')

    @istest
    def test_get_atom_feed_user_loggedin(self):

        env = {'REMOTE_USER': self.user['name'].encode('ascii')}

        resp = self.webtest_app.get(url=self.url, params='format=rss', status=200, expect_errors=False, extra_environ=env)

        assert_equal(resp.status_int, 200)
        assert resp.content_length > 0
        resp.mustcontain('<?xml')
        assert_equal(resp.header('Content-Type'), 'application/atom+xml')

