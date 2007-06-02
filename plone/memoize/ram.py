"""A cache decorator that uses RAMCache.

See README.txt and the `volatile` module for more details.

  >>> def cache_key(fun, first, second):
  ...     return hash((first, second))
  >>> @cache(cache_key)
  ... def pow(first, second):
  ...     print 'Someone or something called me'
  ...     return first ** second

  >>> pow(3, 2)
  Someone or something called me
  9
  >>> pow(3, 2)
  9

Let's cache another function:

  >>> @cache(cache_key)
  ... def add(first, second):
  ...     print 'Someone or something called me'
  ...     return first + second

  >>> add(3, 2)
  Someone or something called me
  5
  >>> add(3, 2)
  5

Now invalidate the cache for the `pow` function:

  >>> pow(3, 2)
  9
  >>> global_cache.invalidate('plone.memoize.ram.pow')
  >>> pow(3, 2)
  Someone or something called me
  9

Make sure that we only invalidated the cache for the `pow` function:

  >>> add(3, 2)
  5

  >>> global_cache.invalidateAll()

You can register an IRAMCacheChooser utility to override the RAMCache
used based on the function that is cached.  To do this, we'll first
unregister the already registered global `choose_cache` function:

  >>> sm = component.getGlobalSiteManager()
  >>> sm.unregisterUtility(choose_cache)
  True

This customized cache chooser will use the `my_cache` for the `pow`
function, and use the `global_cache` for all other functions:

  >>> my_cache = ram.RAMCache()
  >>> def my_choose_cache(fun_name):
  ...     if fun_name.endswith('.pow'):
  ...         return my_cache
  ...     else:
  ...         return global_cache
  >>> interface.directlyProvides(my_choose_cache, IRAMCacheChooser)
  >>> sm.registerUtility(my_choose_cache)

Both caches are empty at this point:

  >>> len(global_cache.getStatistics())
  0
  >>> len(my_cache.getStatistics())
  0

Let's fill them:

  >>> pow(3, 2)
  Someone or something called me
  9
  >>> pow(3, 2)
  9
  >>> len(global_cache.getStatistics())
  0
  >>> len(my_cache.getStatistics())
  1

  >>> add(3, 2)
  Someone or something called me
  5
  >>> add(3, 2)
  5
  >>> len(global_cache.getStatistics())
  1
  >>> len(my_cache.getStatistics())
  1
"""

from zope import interface
from zope import component
from zope.app.cache.interfaces.ram import IRAMCache
from zope.app.cache import ram

from plone.memoize.interfaces import IRAMCacheChooser
from plone.memoize import volatile

global_cache = ram.RAMCache()
DONT_CACHE = volatile.DONT_CACHE

class RAMCacheAdapter:
    def __init__(self, ramcache, globalkey=''):
        self.ramcache = ramcache
        self.globalkey = globalkey

    def __getitem__(self, key):
        marker = object()
        value = self.ramcache.query(self.globalkey, dict(key=key), marker)
        if value is marker:
            raise KeyError(key)
        else:
            return value

    def __setitem__(self, key, value):
        self.ramcache.set(value, self.globalkey, dict(key=key))

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

def choose_cache(fun_name):
    return component.queryUtility(IRAMCache)
interface.directlyProvides(choose_cache, IRAMCacheChooser)

def store_in_ramcache(fun, obj=None, *args, **kwargs):
    key = '%s.%s' % (fun.__module__, fun.__name__)
    cache = component.getUtility(IRAMCacheChooser)(key)
    if cache is None:
        return {}
    else:
        return RAMCacheAdapter(cache, globalkey=key)

def cache(get_key):
    return volatile.cache(get_key, get_cache=store_in_ramcache)
