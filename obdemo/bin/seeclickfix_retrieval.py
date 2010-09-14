from django.contrib.gis.geos import Point
from ebdata.retrieval.scrapers.list_detail import RssListDetailScraper
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem

base_url = 'https://seeclickfix.com/api/'

list_url = base_url + 'issues.rss?at=Boston,+MA'


class SeeClickFixNewsFeedScraper(RssListDetailScraper, NewsItemListDetailScraper):
    schema_slugs = ('local-news',) # TODO: make another type
    has_detail = False

    url = list_url

    def list_pages(self):
        yield self.get_html(self.url)

    def existing_record(self, list_record):
        pk_fields = self.pk_fields(list_record)
        qs = NewsItem.objects.filter(schema__id=self.schema.id, **pk_fields)
        try:
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        kwargs = self.pk_fields(list_record)
        summary_detail = list_record['summary_detail']['value']
        content = list_record['summary']
        # remove address and rating from content, i guess.
        content = content.replace(summary_detail, '')
        import re
        address_re = re.compile(r'Address: (.*?)<br />')
        addr = address_re.search(summary_detail)
        if addr:
            addr = addr.group(1)
            location_name = ', '.join([part.strip() for part in addr.split(',')])
        else:
            location_name = u''

        location = Point((float(list_record['geo_long']),
                          float(list_record['geo_lat'])))

        if (location.x, location.y) == (0,0, 0.0):
            print "skipping %r as it has bad location 0,0" % list_record['title']
            return

        kwargs.update(dict(
                description=list_record['summary_detail']['value'],
                location_name=location_name,
                location=location,
                ))
        if old_record:
            self.update_existing(old_record, kwargs, {})
        else:
            self.create_newsitem(attributes=None, **kwargs)

    def pk_fields(self, list_record):
        # maybe not really primary key, but for this script's
        # purposes these are the fields that uniquely idenfity an article.
        import datetime
        date = datetime.date(*list_record['updated_parsed'][:3])
        return dict(item_date=date,
                    title=u'SeeClickFix: ' + list_record['title'],
                    )


if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    SeeClickFixNewsFeedScraper().update()
