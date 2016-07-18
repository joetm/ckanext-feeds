# encoding: utf-8
""" Feeds extension """

import logging
log = logging.getLogger(__name__)

import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckan.lib.helpers as h

from datetime import datetime

import re
from ckan.lib.base import abort

from ckan.logic.action.get import package_activity_list, user_activity_list, group_activity_list, organization_activity_list

import ckan.model as model
from ckan.common import _, c, g, request, response
from pylons.i18n import get_lang

import ckan.lib.activity_streams as activity_streams
from webhelpers.feedgenerator import Atom1Feed, RssUserland091Feed, Rss201rev2Feed
from ckan.controllers.user import UserController
from ckan.lib.plugins import DefaultTranslation
from ckan.logic.auth.get import dashboard_activity_list as dashboard_auth


class FeedsPlugin(p.SingletonPlugin, DefaultTranslation):
    """
    Several improvements to the feeds
    """

    # enable the custom translations
    p.implements(p.ITranslation)

    p.implements(p.IConfigurer)
    def update_config(self, config):
        # add the template dir
        tk.add_template_directory(config, 'templates')

    # ----------------
    # Template Helpers
    # ----------------
    def get_parameters(self):
        return {
            'format': request.params.get('format', u'rss'),
            'type': request.params.get('type', False),
            'name': request.params.get('name', False)
        }
    p.implements(p.ITemplateHelpers)
    def get_helpers(self):
        return {
            'get_parameters': self.get_parameters
        }


    p.implements(p.IRoutes, inherit=True)

    def before_map(self, map):
        """Iroutes.before_map"""
        map.connect('dashboard_feed',
                    '/dashboard',
                    controller='ckanext.feeds.plugin:DashboardFeedController',
                    action='view_dashboard_feed'
        )
        return map



def rss_snippet_actor(activity, detail, context=None):
    user_dict = tk.get_action('user_show')(context, {'id': activity['user_id']})
    return user_dict['name']


def rss_snippet_user(activity, detail, context=None):
    user_dict = tk.get_action('user_show')(context, {'id': activity['object_id']})
    return user_dict['name']


def rss_snippet_dataset(activity, detail, context=None):
    data = activity['data']
    dataset = data.get('package') or data.get('dataset')
    dataset['url'] = '%s/dataset/%s' % (g.site_url, dataset['name'])
    # return dataset
    return dataset['url']

def rss_snippet_tag(activity, detail, context=None):
    return detail['data']['tag']

def rss_snippet_group(activity, detail, context=None):
    group = h.dataset_display_name(activity['data']['group'])
    return group

def rss_snippet_organization(activity, detail, context=None):
    return h.dataset_display_name(activity['data']['group'])

def rss_snippet_extra(activity, detail, context=None):
    return '"%s"' % detail['data']['package_extra']['key']

def rss_snippet_resource(activity, detail, context=None):
    resource = detail['data']['resource']
    resource['url'] = '%s/dataset/%s' % (g.site_url, resource['url'])
    # return resource
    return resource['url']

def rss_snippet_related_item(activity, detail, context=None):
    return activity['data']['related']

def rss_snippet_related_type(activity, detail, context=None):
    # TODO: this needs to be translated
    return activity['data']['related']['type']


# -----------
# Controllers
# -----------

class DashboardFeedController(UserController):
    """ Dashboard Feed Controller """

    AVAILABLE_FORMATS = ['atom', 'rss']

    RSS_FEED_VERSIONS = ['0.91', '2.01']

    MAXRESULTS = 200

    # A dictionary mapping activity snippets to functions that expand the snippets.
    activity_snippet_functions = {
        'actor': rss_snippet_actor,
        'user': rss_snippet_user,
        'dataset': rss_snippet_dataset,
        'tag': rss_snippet_tag,
        'group': rss_snippet_group,
        'organization': rss_snippet_organization,
        'extra': rss_snippet_extra,
        'resource': rss_snippet_resource,
        'related_item': rss_snippet_related_item,
        'related_type': rss_snippet_related_type,
    }

    def get_feed(self, feed_type='rss', feed_version='2.01'):

        meta = {
            'title': _('News feed'),
            'link': h.url_for(controller='user', action='dashboard', id=''),
            'description': _('Subscribed Activity'), #_("Activity from items that I'm following"),
        }
        lang = get_lang()
        if lang:
            meta['language'] = unicode(lang[0])

        # optional version of feed, e.g. rss 0.91 or rss 2.01 (default)
        if feed_type == 'atom':

            # class webhelpers.feedgenerator.Atom1Feed(title, link, description, language=None, author_email=None, author_name=None, author_link=None, subtitle=None, categories=None, feed_url=None, feed_copyright=None, feed_guid=None, ttl=None, **kwargs)
            feed = Atom1Feed(**meta)

            feed.content_type = 'application/atom+xml'

        elif feed_type == 'rss':

            # if feed_version not in self.RSS_FEED_VERSIONS:
            #     feed_version = '2.01'

            if feed_version == '0.91':

                # class webhelpers.feedgenerator.RssUserland091Feed(title, link, description, language=None, author_email=None, author_name=None, author_link=None, subtitle=None, categories=None, feed_url=None, feed_copyright=None, feed_guid=None, ttl=None, **kwargs)
                feed = RssUserland091Feed(**meta)
            else:

                # class webhelpers.feedgenerator.Rss201rev2Feed(title, link, description, language=None, author_email=None, author_name=None, author_link=None, subtitle=None, categories=None, feed_url=None, feed_copyright=None, feed_guid=None, ttl=None, **kwargs)
                feed = Rss201rev2Feed(**meta)

            feed.content_type = 'application/rss+xml'

        else:
            abort(400, _('Unknown feed format'))

        return feed


    # rewrite of ckan.lib.activity_streams.activity_list_to_html
    def activity_list_to_feed(self, context, activity_stream): # extra_vars={}
        '''Return the given activity stream as a dictionary

        :param context: context dictionary
        :type context: dict
        :param activity_stream: the activity stream to render
        :type activity_stream: list of activity dictionaries
        :param extra_vars: extra variables to pass to the activity stream items
            template when rendering it
        :type extra_vars: dictionary

        :rtype: dict to add to the feed
        '''

        activity_list = [] # These are the activity stream messages.
        for activity in activity_stream:

            # sample activity:
            # {
            # 'user_id': u'082dec4d-1b01-4463-886e-6bb9e5b3a69a',
            # 'timestamp': '2016-06-30T15:42:52.663910',
            # 'is_new': False, 'object_id': u'60e93d90-6fb9-4553-a91f-7089b91af0e3',
            # 'revision_id': u'c257ab4f-5b52-44c4-aee8-807ea6a8a78e',
            # 'data': {u'package': {u'maintainer': u'', u'name': u'test-datasetddd',
            # u'metadata_modified': u'2016-06-30T15:42:51.942624', u'author': u'',
            # u'url': u'http://ogdch.dev/dataset/test-datasetddd', u'notes': u'',
            # u'owner_org': u'2bbf2549-3dd4-40a9-b2c1-e3d1445e0ac6', u'private': False,
            # u'maintainer_email': u'', u'author_email': u'', u'state': u'active',
            # u'version': u'', u'creator_user_id': u'082dec4d-1b01-4463-886e-6bb9e5b3a69a',
            # u'id': u'60e93d90-6fb9-4553-a91f-7089b91af0e3', u'title': u'Test dataset',
            # u'revision_id': u'1d2afe87-4b6b-42c0-a609-c8887c460b52', u'type': u'dataset',
            # u'license_id': u'cc-by'}}, 'id': u'5de15124-72a1-49b0-bdf7-7fde01d4f47b',
            # 'activity_type': u'changed package'
            # }

            detail = None
            activity_type = activity['activity_type']
            # Some activity types may have details.
            if activity_type in activity_streams.activity_stream_actions_with_detail:
                details = tk.get_action('activity_detail_list')(
                    context=context,
                    data_dict={'id': activity['id']}
                )
                # If an activity has just one activity detail then render the
                # detail instead of the activity.
                if len(details) == 1:
                    detail = details[0]
                    object_type = detail['object_type']

                    if object_type == 'PackageExtra':
                        object_type = 'package_extra'

                    new_activity_type = '%s %s' % (detail['activity_type'],
                                                object_type.lower())
                    if new_activity_type in activity_streams.activity_stream_string_functions:
                        activity_type = new_activity_type

            if not activity_type in activity_streams.activity_stream_string_functions:
                raise NotImplementedError("No activity renderer for activity "
                    "type '%s'" % activity_type)

            activity_msg = activity_streams.activity_stream_string_functions[activity_type](context, activity)

            # Get the data needed to render the message.
            matches = re.findall('\{([^}]*)\}', activity_msg)
            data = {}
            for match in matches:
                snippet = self.activity_snippet_functions[match](activity, detail, context)
                data[str(match)] = snippet

            activity_list.append({'msg': activity_msg,
                                  'revision_id': activity['revision_id'],
                                  'object_id': activity['object_id'],
                                  'type': activity_type.replace(' ', '-').lower(),
                                  'title': activity_type.title(),
                                  'data': data,
                                  'timestamp': activity['timestamp'],
                                  'is_new': activity.get('is_new', False)}
                                )

        # extra_vars['activities'] = activity_list
        # return base.render('activity_streams/activity_stream_items.html', extra_vars=extra_vars)

        return activity_list


    def view_dashboard_feed(self, id=None, offset=0):
        """
        Shows the dashboard as a RSS or ATOM feed

        :param id: id
        :type id: string
        :param offset: optional offset for the query
        :type offset: int

        :rtype: rendered dashboard as html or feed
        """

        # check the presence of the 'format' url parameter
        format = request.params.get('format', None)
        if not format:
            # run the dashboard controller instead
            uc = UserController()
            return uc.dashboard(id, offset)

        # check if format is valid
        if format not in self.AVAILABLE_FORMATS:
            abort(400, _('Unknown output format'))

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj,
                   'for_view': True}

        # check if user is logged in
        # if user is not logged, the user is redirected to the login page
        if not dashboard_auth(context, {}).get('success', False):
            abort(401, _('You must be logged in to access your dashboard.'))

        # request parameters
        q = request.params.get('q', u'') # optional query parameter
        filter_type = request.params.get('type', u'') # e.g. 'dataset' to view only the activities related to datasets
        filter_id = request.params.get('name', u'') # e.g. the name or id of the dataset to filter for

        offset = request.params.get('offset', 0)
        limit = request.params.get('limit', 0)

        # TODO: this would allow to view only unread items
        is_new = bool(request.params.get('is_new', False))

        self._setup_template_variables(context, {'id': id, 'user_obj': c.userobj, 'offset': offset})

        c.followee_list = tk.get_action('followee_list')(context, {'id': c.userobj.id, 'q': u''})
        c.dashboard_activity_stream_context = self._get_dashboard_context(filter_type, filter_id, q)

        # https://github.com/ckan/ckan/blob/55ae76ec73e97bcae05b778ab35f23ed518e6e24/ckan/controllers/user.py#L672

        query_dict = {
            'id': filter_id,
            'offset': offset,
            'limit': limit,
        }

        if filter_type == 'dataset':

            activity_stream = package_activity_list(context, query_dict)

        elif filter_type == 'user':

            activity_stream = user_activity_list(context, query_dict)

        elif filter_type == 'group':

            activity_stream = group_activity_list(context, query_dict)

        elif filter_type == 'organization':

            activity_stream = organization_activity_list(context, query_dict)

        else:

            # full, unfiltered, activity stream
            # activity_stream = h.dashboard_activity_stream(c.user, filter_type, filter_id, offset)
            activity_stream = tk.get_action('dashboard_activity_list')(context, {
                'offset': offset,
                'is_new': is_new,
            })

        # log.debug('activity_stream: %s' % activity_stream)

        activity_list = self.activity_list_to_feed(context, activity_stream)

        # activity_list_limit = int(g.activity_list_limit)
        # has_more = len(activity_list) > activity_list_limit

        # feed object
        feed = self.get_feed(feed_type=format, feed_version=request.params.get('version', '2.01'))

        for activity in activity_list:

            log.debug(activity['msg'])

            activity['msg'] = activity['msg'].format(**activity['data'])

            # http://docs.pylonsproject.org/projects/webhelpers/en/latest/modules/feedgenerator.html#webhelpers.feedgenerator.SyndicationFeed.add_item
            # required fields: title, link, description
            # optional fields: author_email, author_name, author_link, pubdate, comments, unique_id, enclosure, categories, item_copyright, ttl, **kwargs
            feed.add_item(
                title=_(activity['title']),
                link='%s/revision/%s' % (g.site_url, activity['revision_id']),
                description=activity['msg'],
                author_name=activity['data']['actor'],
                pubdate=datetime.strptime(activity['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'), # '2016-06-30T15:42:52.663910'
                unique_id=activity['object_id'],
            )

        # Mark the user's new activities as old whenever they view their dashboard feed
        tk.get_action('dashboard_mark_activities_old')(context, {})

        return feed.writeString('utf-8')

