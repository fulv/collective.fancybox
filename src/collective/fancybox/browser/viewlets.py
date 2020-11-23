# -*- coding: utf-8 -*-
from collective.fancybox.interfaces import ICollectiveFancyboxMarker
from collective.fancybox.interfaces import ICollectiveFancyboxMarkerGlobal
from plone import api
from plone.app.layout.viewlets.common import ViewletBase
from z3c.relationfield.index import dump
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.interface import providedBy

import logging


log = logging.getLogger(__name__)


class hasLightbox(object):
    """ Used by the viewlet and by the bundle expression property. """

    def __call__(self):
        self.target = None
        self.portal = api.portal.get()
        enabled = self._hasLocalMarker() or self._hasGlobalMarker()

        if not enabled:
            return False

        self.lightbox = self._findLightbox()
        if not self.lightbox:
            return False

        enabled = self._isPublished() and self._isEffective()

        if not enabled:
            return False

        enabled = self._showFirstTimeOrReturning()
        return enabled and self.lightbox

    def _hasLocalMarker(self):
        """Does context have the marker?"""
        if ICollectiveFancyboxMarker in providedBy(self.context):
            self.target = self.context
        return bool(self.target)

    def _hasGlobalMarker(self):
        """Does portal have the global marker?"""
        if ICollectiveFancyboxMarkerGlobal in providedBy(self.portal):
            self.target = self.portal
        return bool(self.target)

    def _findGlobalLightbox(self):
        """ query the catalog for lightbox_where == 'everywhere'
            because the portal does not have an int_id
        """
        obj = None
        query = {'lightbox_where': 'everywhere'}
        for result in api.content.find(**query):
            try:
                if obj is None:
                    obj = result.getObject()
                else:
                    p1 = obj.absolute_url_path()
                    p2 = result.getObject().absolute_url_path()
                    raise RuntimeError(
                        # log.error(
                        'There should be at most one global marker. '
                        'Found: {0} and: {1}. (There may or may not '
                        'be others.)'.format(p1, p2)
                    )
            except Exception:
                log.error(
                    'Not possible to fetch object from catalog result for '
                    'item: {0}.'.format(result.getPath()))
                raise
        # there should only be one
        return obj
        log.warning('We have ICollectiveFancyboxMarkerGlobal but no lightbox')
        return None

    def _findLocalLightbox(self):
        """ Look for relations of type Lightbox that point here."""
        cat = getUtility(ICatalog)
        int_id = dump(self.context, cat, {})

        if int_id:
            rels = cat.findRelations(dict(to_id=int_id))
            relations = [r for r in rels]
            for relation in (relations or []):
                if not relation.isBroken():
                    obj = relation.from_object
                    if hasattr(obj, 'portal_type'):
                        if obj and obj.portal_type == 'Lightbox':
                            return obj
        log.warning('We have ICollectiveFancyboxMarker but no lightbox')
        return None

    def _findLightbox(self):
        """ Find the lightbox object that points to self.target. """
        if self.target == self.portal:
            return self._findGlobalLightbox()
        else:
            return self._findLocalLightbox()

    def _hasCookie(self):
        pass

    def _isPublished(self):
        return api.content.get_state(self.lightbox) == 'published'

    def _isEffective(self):
        lb = self.lightbox
        return lb.effective().isPast() and lb.expires().isFuture()

    def _showFirstTimeOrReturning(self):
        """ If there is a cookie, visitor has already seen the lightbox.
            We assume first time visitor if there is no cookie.
            In the latter case, set the cookie.
            *Note to self*: this is called at least twice for each page load,
            1. from the bundle expression='context/@@hasLightbox'
            2. from the viewlet.
        """
        id = 'collective.fancybox.{}'.format(self.lightbox.id)
        effective = self.lightbox.effective()
        expires = self.lightbox.expires()
        timestamp = str(effective.asdatetime().timestamp())
        if (self.lightbox.lightbox_repeat != 'always'):
            cookie = self.request.cookies.get(id)
            if cookie == timestamp:
                return False
            else:
                self.request.response.setCookie(
                    id,
                    timestamp,
                    expires=expires.rfc822()
                )
                return True
        else:
            return True


class LightboxViewlet(ViewletBase):

    def update(self):
        super(LightboxViewlet, self).update()
        self.lightbox = self.context.unrestrictedTraverse('@@hasLightbox')()
        self.enabled = bool(self.lightbox)
