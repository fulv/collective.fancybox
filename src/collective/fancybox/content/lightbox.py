# -*- coding: utf-8 -*-
from collective.fancybox import _
from collective.fancybox.interfaces import ICollectiveFancyboxMarker
from collective.fancybox.interfaces import ICollectiveFancyboxMarkerGlobal
from plone import api
from plone.app.z3cform.widget import RelatedItemsFieldWidget
from plone.autoform import directives
from plone.dexterity.content import Item
from plone.indexer.decorator import indexer
from plone.supermodel import model
from z3c.form.browser.radio import RadioFieldWidget
from z3c.relationfield.schema import RelationChoice
from z3c.relationfield.schema import RelationList
from z3c.relationfield import RelationValue
from zope import schema
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from zope.interface import implementer
from zope.interface import Invalid
from zope.interface import invariant
from zope.interface import providedBy
from zope.intid.interfaces import IIntIds
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import logging


log = logging.getLogger(__name__)


class ILightbox(model.Schema):
    """ Marker interface and Dexterity Python Schema for Lightbox
    """
    directives.widget(lightbox_repeat=RadioFieldWidget)
    lightbox_repeat = schema.Choice(
        title=_(u'How often shall this lightbox be shown?'),
        vocabulary=SimpleVocabulary([
            SimpleTerm(value=u'once', title=u'Once'),
            SimpleTerm(value=u'always', title=u'Always'),
        ]),
        required=False,
        default=u'always',
    )

    directives.widget(lightbox_where=RadioFieldWidget)
    lightbox_where = schema.Choice(
        title=_(u'Which pages will this lightbox be shown on?'),
        vocabulary=SimpleVocabulary([
            SimpleTerm(value=u'nowhere', title=u'Nowhere (Disabled)'),
            SimpleTerm(value=u'everywhere', title=u'Everywhere'),
            SimpleTerm(value=u'select', title=u'On the pages selected below only'),
        ]),
        required=False,
        default=u'everywhere',
    )

    lightbox_targets = RelationList(
        title=u"Show the lightbox on these pages",
        default=[],
        value_type=RelationChoice(vocabulary='plone.app.vocabularies.Catalog'),
        required=False,
        missing_value=[],
    )
    directives.widget(
        "lightbox_targets",
        RelatedItemsFieldWidget,
        vocabulary='plone.app.vocabularies.Catalog',
    )

    lightbox_url = schema.URI(
        title=u"URL",
        description=u"Open this URL when the lightbox is clicked",
        required=False,
    )

    @invariant
    def validate_lightbox(data):
        if data.lightbox_where == u'select':
            if not data.lightbox_targets:
                raise Invalid(_('You did not pick a page for your lightbox'))
        if data.lightbox_where == u'everywhere':
            old_where = getattr(data.__context__, 'lightbox_where', None)
            if old_where != data.lightbox_where:
                msg = 'Another lightbox already shows everywhere {0}'
                marker = ICollectiveFancyboxMarkerGlobal in providedBy(api.portal.get())
                if marker:
                    query = {'lightbox_where': 'everywhere'}
                    results = api.content.find(**query)
                    if len(results) > 0:
                        slot = results[0].getPath()
                    else:
                        slot = ''
                    raise Invalid(msg.format(slot))


@implementer(ILightbox)
class Lightbox(Item):
    """
    """


@indexer(ILightbox)
def lightbox_where(object, **kw):
    return object.lightbox_where


@indexer(ILightbox)
def lightbox_repeat(object, **kw):
    return object.lightbox_repeat


def clearGlobalMarker(context):
    noLongerProvides(context, ICollectiveFancyboxMarkerGlobal)


def clearLocalMarker(context):
    noLongerProvides(context, ICollectiveFancyboxMarker)


def hasGlobalMarker():
    return ICollectiveFancyboxMarkerGlobal in providedBy(api.portal.get())


def hasLocalMarker(context):
    return ICollectiveFancyboxMarker in providedBy(context)


# def setGlobalMarker():
#     alsoProvides(api.portal.get(), ICollectiveFancyboxMarkerGlobal)


def setLocalMarker(context):
    alsoProvides(context, ICollectiveFancyboxMarker)


def getRelationValue(context):
    intids = getUtility(IIntIds)
    return RelationValue(intids.getId(context))


def getGlobalLightbox():
    obj = None
    query = {'lightbox_where': 'everywhere'}
    for result in api.content.find(**query):
        try:
            if not obj:
                obj = result.getObject()
            else:
                log.error(
                    'There should be at most one global '
                    'lightbox: {0}.'.format(result.getPath())
                )
        except Exception:
            log.error(
                'Not possible to fetch object from catalog result for '
                'item: {0}.'.format(result.getPath())
            )
    return obj


def canSetGlobalMarker(lightbox):
    obj = getGlobalLightbox()
    return (obj is None) or (obj == lightbox)
