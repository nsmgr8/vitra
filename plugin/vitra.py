# -*- encoding: utf-8 -*-

import codecs
import datetime
import os.path
import re
import urllib2
import vim
import webbrowser
import xmlrpclib


trac = None


def confirm(text):
    return int(vim.eval('confirm("{0}", "&Yes\n&No", 2)'.format(text))) != 2


def truncate_words(text, num_words=10):
    words = text.split()
    if len(words) <= num_words:
        return text
    return ' '.join(words[:num_words]) + '...'


def get_time(value, format=False):
    if isinstance(value, xmlrpclib.DateTime):
        dt = datetime.datetime.strptime(value.value, "%Y%m%dT%H:%M:%S")
    else:
        dt = datetime.datetime.fromtimestamp(value)
    return dt.strftime("%a %d/%m/%Y %H:%M") if format else dt


def save_buffer(buffer, file):
    file_name = os.path.basename(file)
    if os.path.exists(file_name):
        vim.command('echoerr "File \'{0}\' exists!"'.format(file_name))
    else:
        with open(file_name, 'wb') as fp:
            fp.write(buffer)


def save_html(html):
    file_name = vim.eval('tracTempHtml')
    with codecs.open(file_name, 'w', 'utf-8') as fp:
        fp.write(html)
    return file_name


def map_commands(nmaps):
    for m in nmaps:
        vim.command('nnoremap <buffer> {0} {1}'.format(*m))


def print_error(e):
    err = str(e)
    if '"' in err:
        print err
    else:
        vim.command('echoerr "Error: {0}"'.format(err))


class HTTPDigestTransport(xmlrpclib.Transport):
    def __init__(self, scheme, username, password, realm):
        xmlrpclib.Transport.__init__(self)
        self.username = username
        self.password = password
        self.realm = realm
        self.scheme = scheme

    def request(self, host, handler, request_body, verbose):
        url = '{scheme}://{host}{handler}'.format(scheme=self.scheme,
                                                  host=host, handler=handler)
        self.verbose = verbose
        request = urllib2.Request(url)
        request.add_data(request_body)
        request.add_header("User-Agent", self.user_agent)
        request.add_header("Content-Type", "text/xml")

        authhandler = urllib2.HTTPDigestAuthHandler()
        authhandler.add_password(self.realm, url, self.username, self.password)
        opener = urllib2.build_opener(authhandler)
        f = opener.open(request)
        return self.parse_response(f)


class Window(object):
    def __init__(self, prefix='TYPE', name='WINDOW'):
        self.name = name
        self.prefix = prefix
        self.buffer = []

    @property
    def buffer_name(self):
        return '{0}:\ {1}'.format(self.prefix, self.name)

    @property
    def winnr(self):
        return int(vim.eval("bufwinnr('{0}')".format(self.buffer_name)))

    @property
    def content(self):
        return "\n".join(self.buffer)

    @property
    def height(self):
        return int(vim.eval("winheight('{0}')".format(self.winnr)))

    @property
    def width(self):
        return int(vim.eval("winwidth('{0}')".format(self.winnr)))

    @property
    def size(self):
        return (self.width, self.height)

    def set_name(self, name):
        self.focus()
        self.name = name
        vim.command('silent f {0}'.format(self.buffer_name))

    def create(self, method='new'):
        if self.winnr > 0:
            return False
        vim.command('silent {0} {1}'.format(method, self.buffer_name))
        vim.command("setlocal buftype=nofile")
        vim.command('setlocal noswapfile')
        self.buffer = vim.current.buffer
        self.on_create()
        return True

    def destroy(self):
        self.command('bdelete {0}'.format(self.buffer_name))

    def write(self, text):
        text = text.encode('utf-8', 'ignore')
        self.prepare()
        vim.command("setlocal modifiable")
        self.buffer[:] = text.splitlines()
        self.on_write()

    def clear(self):
        self.prepare()
        self.command('setlocal modifiable')
        self.buffer[:] = []

    def on_create(self):
        pass

    def on_write(self):
        vim.command('normal gg')

    def command(self, cmd):
        self.prepare()
        vim.command(cmd)

    def prepare(self):
        if self.winnr < 0:
            self.create()
        self.focus()

    def focus(self):
        vim.command('{0}wincmd w'.format(self.winnr))

    def resize(self, width=None, height=None):
        if width is not None:
            self.command('vertical resize {0}'.format(width))
        if height is not None:
            self.command('resize {0}'.format(height))


class NonEditableWindow(Window):
    def on_write(self):
        vim.command("setlocal nomodifiable")
        super(NonEditableWindow, self).on_write()


class UI(object):
    windows = {}

    def create(self):
        for window in self.windows.values():
            window.create()

    def destroy(self):
        for window in self.windows.values():
            window.destroy()

    def update(self, contents, titles):
        for window in contents:
            self.windows[window].write(contents[window])
        for window in titles:
            self.windows[window].set_name(titles[window])

    def focus(self, window):
        self.windows[window].focus()


class WikiUI(UI):
    def __init__(self):
        self.windows = {
            'wiki': WikiWindow(prefix='Wiki'),
            'preview': PreviewWindow(prefix='Wiki', name='Preview'),
            'list': WikiListWindow(prefix='Wiki', name='List\ of\ pages'),
            'attachment': AttachmentWindow(prefix='Wiki', name='Attachment'),
        }

    def create(self):
        if vim.eval('tracWikiStyle') == 'full':
            if self.windows['wiki'].create():
                vim.command("only")
        else:
            self.windows['wiki'].create("vertical belowright new")
        if vim.eval('tracWikiToC') == '1':
            self.windows['list'].create('vertical leftabove new')
        self.focus('wiki')
        if vim.eval('tracWikiPreview') == '1':
            w, h = self.windows['wiki'].size
            w = w / 2
            if w > h:
                position = 'vertical belowright new'
            else:
                position = 'aboveleft new'
            if self.windows['preview'].create(position) and w > h:
                self.windows['preview'].resize(width=min(w, 85))
        self.focus('wiki')
        self.windows['attachment'].create('belowright 3 new')


class TicketUI(UI):
    def __init__(self):
        self.windows = {
            'ticket': TicketWindow(prefix='Ticket'),
            'edit': TicketCommentWindow(prefix='Ticket', name='Edit'),
            'list': TicketListWindow(prefix='Ticket', name='Listing'),
            'attachment': AttachmentWindow(prefix='Ticket', name='Attachment'),
        }

    def create(self):
        if vim.eval('tracTicketStyle') == 'full':
            if self.windows['ticket'].create('belowright new'):
                vim.command('only')
            w = self.windows['ticket'].width / 2
            h = self.windows['ticket'].height / 2
            if self.windows['list'].create('leftabove new'):
                self.windows['list'].resize(height=min(h, 20))
            self.focus('ticket')
            if self.windows['edit'].create('vertical belowright new'):
                self.windows['edit'].resize(width=min(w, 85))
        else:
            self.windows['ticket'].create("belowright new")
            self.windows['edit'].create("belowright new")
        self.focus('edit')
        self.windows['attachment'].create('belowright 3 new')


class WikiWindow(Window):
    def on_create(self):
        map_commands([
            ('<c-]>', ':python trac.wiki_view("<c-r><c-w>")<cr>'),
            ('wo', 'f:lmy/[ \]]<cr>:nohl<cr>hv`y"zy'
                   ':python trac.wiki_view("<c-r>z")<cr>'),
            ('w]', '/[\[\"]<cr>:nohl<cr>lmy/[\]\"]<cr>:nohl<cr>hv`y"zy'
                   ':python trac.wiki_view("<c-r>z")<cr>'),
            ('<2-LeftMouse>', ':python trac.wiki_view("<c-r><c-w>")<cr>'),
            (':w<cr>', ':TWSave<cr>'),
            ('<tab>',  '/^=.*=<cr>:nohl<cr>'),
            ('<c-tab>', '/\\(wiki:\\\|[[\\\|\<[A-Z][a-z]*[A-Z]\\)<cr>'
                        ':nohl<cr>'),
            ('<c-l>', ':python trac.wiki_view()<cr><c-l>'),
        ])
        vim.command('setlocal syntax=tracwiki')


class PreviewWindow(NonEditableWindow):
    def on_create(self):
        vim.command('syn match Keyword /\[\d*\]\w*/ contains=Ignore')
        vim.command('syn match Ignore /\[\d*\]/ contained')
        map_commands([
            ('<tab>', '/\\d*\\]\\w*<cr>:nohl<cr>'),
            ('<cr>', 'F[l/^ *<c-r><c-w>. http<cr>fh"py$:nohl<cr>'
                     ':python webbrowser.open("<c-r>p")<cr><c-o>'),
        ])

    def load(self, html):
        file_name = save_html(html)
        self.clear()
        self.command('silent r!lynx -dump {0}'.format(file_name))
        self.on_write()


class WikiListWindow(NonEditableWindow):
    def on_create(self):
        map_commands([
            ('<cr>', ':python trac.wiki_view(vim.current.line)<cr>'),
            ('<2-LeftMouse>', ':python trac.wiki_view(vim.current.line)<cr>'),
        ])
        vim.command('vertical resize 30')

    def on_write(self):
        if vim.eval('tracHideTracWiki') == '1':
            for name in ('Trac', 'Wiki', 'InterMapTxt$', 'InterWiki$',
                         'InterTrac$', 'SandBox$', 'TitleIndex$',
                         'RecentChanges$', 'CamelCase$', 'PageTemplates$'):
                vim.command('silent g/^{0}/d _'.format(name))

        vim.command('sort')
        vim.command('silent norm ggOWikiStart')
        super(WikiListWindow, self).on_write()


class TicketListWindow(NonEditableWindow):
    def on_create(self):
        map_commands([
            ('<cr>', '0:python trac.ticket_view("<c-r><c-w>")<cr>'),
            ('<2-LeftMouse>', '0:python trac.ticket_view("<c-r><c-w>")<cr>'),
            ('<c-l>', ':python trac.ticket_view()<cr><c-l>'),
        ])

    def on_write(self):
        try:
            vim.command('AlignCtrl rl+')
            vim.command('%Align ||')
        except:
            vim.command('echo "install Align for the best view of summary"')
        vim.command('silent %s/^\s*|| / - /g')
        super(TicketListWindow, self).on_write()
        vim.command('silent norm 2gg')
        vim.command('syn match Ignore /||/')
        vim.command('syn match Number /\<\d*\>/')
        vim.command('syn match Error /^\s*#.*$/')
        vim.command('syn match Keyword /^\s-\s.*: .*$/ contains=Title')
        vim.command('syn match Title /^\s-\s.*:/ contained')
        hilighters = ['Constant', 'Special', 'Identifier', 'Statement',
                      'PreProc', 'Type', 'Underlined']
        num_hi = len(hilighters)
        options = trac.ticket.options
        for values in options.values():
            for i, a in enumerate(values):
                try:
                    float(a)
                except ValueError:
                    hi = hilighters[i % num_hi]
                    vim.command('syn match {0} /\<{1}\>/'.format(hi,
                                a.replace('/', '\/')))


class TicketWindow(NonEditableWindow):
    def on_write(self):
        super(TicketWindow, self).on_write()
        map_commands([
            ('<tab>', '/^=.*=<cr>:nohl<cr>'),
            ('<c-l>', ':python trac.ticket_view()<cr><c-l>'),
        ])

    def on_create(self):
        vim.command('setlocal syntax=tracwiki')
        vim.command('syn match Keyword /^ \+\*[^:]*:.*$/ contains=Title')
        vim.command('syn match Title /^ \+\*[^:]*:/ contained')
        vim.command('syn match Underlined /\[\d*\]\w*/ contains=Ignore')
        vim.command('syn match Ignore /\[\d*\]/ contained')
        vim.command('syn match Special '
                    '/\w\{3\} [0-9/]\{10\} [0-9:]\{5\} (.*)/ '
                    'contains=Identifier')
        vim.command('syn match Identifier /(.*)/ contained')

    def load(self, wiki_text):
        try:
            file_name = save_html(trac.server.wiki.wikiToHtml(wiki_text))
        except Exception as e:
            print_error(e)
            return
        self.clear()
        self.command('silent r!lynx -dump {0}'.format(file_name))
        self.on_write()
        map_commands([
            ('<tab>',
                '/^\w\{3\} [0-9/]\{10\} [0-9:]\{5\} (.*)$<cr>:nohl<cr>'),
            ('<c-]>', '/\\d*\\]\\w*<cr>:nohl<cr>'),
            ('<cr>', 'F[l/^ *<c-r><c-w>. http<cr>fh"py$:nohl<cr>'
                    ':python webbrowser.open("<c-r>p")<cr><c-o>'),
        ])


class TicketCommentWindow(Window):
    def on_create(self):
        vim.command('setlocal syntax=tracwiki')


class SearchWindow(NonEditableWindow):
    def on_create(self):
        map_commands([
            ('<tab>', '/^\w\+:>><cr>:nohl<cr>'),
            ('<c-]>', ':python trac.wiki_view("<c-r><c-w>")<cr>'),
            ('<cr>', ':python trac.open_line()<cr>'),
        ])
        vim.command('setlocal syntax=tracwiki')
        vim.command('syn match Keyword /\w*:>> .*$/ contains=Title')
        vim.command('syn match Title /\w*:>>/ contained')


class TimelineWindow(SearchWindow):
    def on_create(self):
        super(TimelineWindow, self).on_create()
        vim.command('syn match Identifier /^[0-9\-]\{10\}\s.*$/ '
                    'contains=Statement')
        vim.command('syn match Statement /[0-9:]\{8\}$/ contained')


class ServerWindow(NonEditableWindow):
    def on_create(self):
        vim.command('syn match Keyword /^\w*:/')
        vim.command('syn match Identifier /^\*\w*:/')
        vim.command('syn match Title /^!\w*:/')
        vim.command('syn match Special /^\*!\w*:/')
        map_commands([
            ('<cr>', '0:python trac.server="<c-r><c-w>"<cr>'
                     ':python trac.server_view()<cr>')])


class AttachmentWindow(NonEditableWindow):
    def on_create(self):
        map_commands([
            ('<cr>', ':python trac.get_attachment(vim.current.line)<cr>')])


class ChangesetWindow(NonEditableWindow):
    def load(self, changeset):
        self.clear()
        self.command('silent Nread {0}?format=diff'.format(changeset))
        self.command('0d_')
        self.command('set ft=diff')
        self.command('silent %s/\r//g')
        self.on_write()


class Wiki(object):
    def __init__(self):
        self.initialise()

    def initialise(self):
        self.pages = []
        self.current = {}

    def get_all(self):
        try:
            self.pages = trac.server.wiki.getAllPages()
            return self.pages
        except Exception as e:
            print_error(e)
            return []

    def get(self, name):
        try:
            name = name.strip()
            self.attachments = []
            self.current = {'name': name}
            mc = xmlrpclib.MultiCall(trac.server)
            mc.wiki.getPage(name)
            mc.wiki.getPageInfo(name)
            mc.wiki.listAttachments(name)
            text, info, attachments = [c for c in mc()]
            self.current = info
            self.attachments = attachments
        except xmlrpclib.Fault as e:
            if e.faultCode == 404:
                text = "Page doesn't exist. Describe {0} here.".format(name)
            else:
                text = "Error: {0}".format(e.faultString)
        except Exception as e:
                text = "Error: {0}".format(e)
        return text

    def get_html(self):
        if not self.current.get('name'):
            return ''
        try:
            return trac.server.wiki.getPageHTML(self.current.get('name'))
        except Exception as e:
            return str(e)

    def save(self, comment):
        try:
            info = trac.server.wiki.getPageInfo(self.current.get('name'))
            if (get_time(info['lastModified']) >
                    get_time(self.current.get('lastModified'))):
                vim.command("echoerr 'This page has been modified in another "
                            "session. Not commiting the changes.'")
                return False
        except:
            if not confirm('Cannot confirm last modification time.\n'
                           'Do you want to continue to save?'):
                return False
        if not comment:
            comment = trac.default_comment
        try:
            trac.server.wiki.putPage(self.current.get('name'),
                trac.wiki_content, {"comment": comment})
            return True
        except xmlrpclib.Fault as e:
            vim.command('echoerr "Not committing the changes."')
            vim.command('echoerr "Error: {0}"'.format(e.faultString))
        except Exception as e:
            print_error(e)
        return False

    def add_attachment(self, file):
        file_name = os.path.basename(file)
        path = '{0}/{1}'.format(self.current.get('name'), file_name)
        attachment = xmlrpclib.Binary(open(file).read())
        try:
            trac.server.wiki.putAttachment(path, attachment)
            return True
        except Exception as e:
            print_error(e)
            return False

    def get_attachment(self, file):
        try:
            buffer = trac.server.wiki.getAttachment(file)
            save_buffer(buffer.data, file)
            return True
        except Exception as e:
            print_error(e)
            return False

    def get_options(self):
        if not self.pages:
            self.get_all()
        vim.command('let g:tracOptions={0}'.format(self.pages))


class Ticket(object):
    def __init__(self):
        self.fields = []
        self.options = {}
        self.initialise()

    def initialise(self):
        self._delete_vim_commands()
        self.current = {}
        self.fields = []
        self.options = {}
        self.actions = []
        self.tickets = []
        self.sorter = {
            'order': vim.eval('tracTicketOrder'),
            'group': vim.eval('tracTicketGroup'),
        }
        self.filters = {}
        self.page = 1
        self.total_pages = 0
        self.attachments = []

    def get_fields(self):
        if self.fields:
            return
        try:
            fields = trac.server.ticket.getTicketFields()
        except Exception as e:
            print_error(e)
            return
        self.options = {}
        self.fields = fields
        for f in fields:
            if 'options' in f:
                self.options[f['name']] = f['options']
        self.max_label_width = max([len(f['label']) for f in self.fields])
        self._generate_vim_commands()

    def _delete_vim_commands(self):
        for t in self.options.get('type', []):
            name = t.title()
            name = ''.join(re.findall('[a-zA-z0-9]*', name))
            vim.command('delc TTCreate{0}'.format(name))
        delcommand = """
            if exists(':TT{0}{1}') == 2
                delc TT{0}{1}
            endif
            if exists('*Com{1}')
                delf Com{1}
            endif
        """
        for f in self.fields:
            mname = f['name'].title()
            mname = ''.join(re.findall('[a-zA-Z0-9]*', mname))
            for s in ('Update', 'Filter', 'Ignore'):
                vim.command(delcommand.format(s, mname))

    def _generate_vim_commands(self):
        for t in self.options['type']:
            name = t.title()
            name = ''.join(re.findall('[a-zA-z0-9]*', name))
            name = 'TTCreate{0}'.format(name)
            meth = 'python trac.create_ticket("{0}", <q-args>)'.format(t)
            vim.command('com! -nargs=+ {0} {1}'.format(name, meth))

        compfun = """
            fun! Com{0}(A, L, P)
                python trac.ticket.get_options('{1}')
                let l:comp = 'v:val =~ "^' . a:A . '"'
                return filter(g:tracOptions, l:comp)
            endfun
        """

        for f in self.fields:
            if f['type'] == 'time' or f['name'] in ('summary', 'description'):
                continue
            fname = f['name']
            mname = fname.title()
            mname = ''.join(re.findall('[a-zA-Z0-9]*', mname))
            if 'options' in f:
                comp = '-complete=customlist,Com{0}'.format(mname)
                vim.command(compfun.format(mname, fname))
            else:
                comp = ''
            for s in ('update', 'filter', 'ignore'):
                if s == 'update' and mname in ('Owner', 'Reporter',
                                               'Resolution', 'Status'):
                    continue
                name = 'TT{0}{1}'.format(s.title(), mname)
                mc = 'python trac.{0}_ticket("{1}", <q-args>)'.format(s, fname)
                command = 'com! -nargs=? {0} {1} {2}'.format(comp, name, mc)
                vim.command(command)

    def get_label(self, field):
        for f in self.fields:
            if f['name'] == field:
                return f['label']
        return field.title()

    def set_sort_attr(self, attrib, value):
        self.sorter[attrib] = value

    def query_string(self, f_all=False):
        query = 'order={order}&group={group}&page={page}'
        query = query.format(page=self.page, **self.sorter)
        query = '{0}&{1}'.format(query, vim.eval('tracTicketClause'))
        filters = ['{0}={1}'.format(k, v) for k, v in self.filters.iteritems()]
        if filters:
            query = '{0}&{1}'.format(query, '&'.join(filters))
        if f_all:
            query = '{0}&max=0'.format(query)
        return query

    @property
    def number_tickets(self):
        try:
            total = len(trac.server.ticket.query(self.query_string(True)))
        except Exception as e:
            print_error(e)
            self.total_pages = 0
            return 0
        max_regex = re.compile('max=(\d*)')
        res = max_regex.search(self.query_string())
        if res:
            tickets_per_page = res.groups()[0]
            if tickets_per_page == '0':
                tickets_per_page = total
        else:
            tickets_per_page = 100
        tp = total / float(tickets_per_page)
        if int(tp) < tp:
            tp += 1
        self.total_pages = int(tp)
        return total

    def get_all(self):
        multicall = xmlrpclib.MultiCall(trac.server)
        try:
            for ticket in trac.server.ticket.query(self.query_string()):
                multicall.ticket.get(ticket)
        except Exception as e:
            return ' || Error: {0}'.format(e)
        tickets = multicall()
        self.tickets = tickets

        columns = ['#', 'summary']
        columns.extend(self.options.keys())
        columns.extend(['owner', 'reporter'])
        if 'resolution' in columns:
            columns.remove('resolution')

        tlist = [' || '.join([c.title() for c in columns])]
        try:
            for ticket in tickets:
                str_ticket = [str(ticket[0]),
                              truncate_words(ticket[3]['summary'])]
                for f in columns[2:]:
                    str_ticket.append(ticket[3].get(f, ''))
                tlist.append(' || '.join(str_ticket))
        except Exception as e:
            return ' || Error: {0}'.format(e)

        skey = ' || {0}: {1}'
        tlist.append('')
        for k, v in self.sorter.iteritems():
            tlist.append(skey.format(k.title(), self.get_label(v)))
        for k, v in self.filters.iteritems():
            tlist.append(skey.format(k.title(), self.get_label(v)))

        tlist.extend([skey.format('Other', vim.eval('tracTicketClause')),
            '', skey.format('Number of tickets', self.number_tickets),
            ' || {0}: {1} of {2}'.format('Page', self.page, self.total_pages)])
        tlist.append('')
        return "\n".join(tlist)

    def get(self, tid):
        try:
            tid = int(tid)
            mc = xmlrpclib.MultiCall(trac.server)
            mc.ticket.get(tid)
            mc.ticket.changeLog(tid)
            mc.ticket.listAttachments(tid)
            mc.ticket.getActions(tid)
            ticket, changelog, attachments, actions = [c for c in mc()]
            self.current = {
                'id': tid,
                '_ts': ticket[3].get('_ts'),
                'summary': ticket[3]['summary'],
                'description': ticket[3]['description'],
            }
            self.get_actions(actions=actions)
            self.attachments = [a[0] for a in attachments]
        except (TypeError, ValueError):
            return 'Please select a ticket'
        except Exception as e:
            return 'An error occured:\n\t{0}'.format(e)

        sticket = ["= Ticket #{0} =".format(tid), ""]
        for f in self.fields:
            if f['name'] == 'description':
                continue
            if f['type'] == 'time':
                v = get_time(ticket[3][f['name']], True)
            else:
                v = ticket[3].get(f['name'], '')
            sticket.append(u' * {0:>{2}}: {1}'.format(f['label'], v,
                                                     self.max_label_width))

        sticket.extend(["", "= Description =",
                        "", ticket[3]["description"],
                        "", "= Changelog ="])

        ctime = [None, None]
        for change in changelog:
            if not change[4] or change[2].startswith('_'):
                continue

            my_time = get_time(change[0], True)
            nctime = [my_time, change[1]]
            if ctime != nctime:
                sticket.extend(["", u'== {0} ({1}) =='.format(*nctime), ""])
                ctime = nctime
            if change[2] == 'comment':
                sticket.append(change[4])
            elif change[2] in ('summary', 'description'):
                sticket.append("{0} changed".format(change[2]))
            else:
                changes = (self.get_label(change[2]), change[3], change[4])
                csf = u' * {0}: {1} > {2}' if change[3] else u' * {0}: {2}'
                sticket.append(csf.format(*changes))

        sticket.extend(["", '== Action ==', ""])
        sticket.extend([' - {0}'.format(action[0]) for action in actions])
        return '\n'.join(sticket)

    def update(self, comment, attribs={}, notify=False):
        try:
            if self.current.get('_ts'):
                attribs['_ts'] = self.current['_ts']
            return trac.server.ticket.update(self.current['id'], comment,
                                             attribs, notify)
        except xmlrpclib.Fault as e:
            vim.command("echoerr 'Not committing the changes.'")
            vim.command('echoerr "Error: {0}"'.format(e.faultString))
        return None

    def create(self, description, summary, attributes={}):
        try:
            return trac.server.ticket.create(summary, description, attributes)
        except Exception as e:
            print_error(e)
            return None

    def get_attachment(self, file):
        try:
            buffer = trac.server.ticket.getAttachment(self.current.get('id'),
                                                      file)
            save_buffer(buffer.data, file)
            return True
        except Exception as e:
            print_error(e)
            return False

    def add_attachment(self, file, comment=''):
        file_name = os.path.basename(file)
        try:
            trac.server.ticket.putAttachment(self.current.get('id'), file_name,
                comment, xmlrpclib.Binary(open(file).read()))
            return True
        except Exception as e:
            print_error(e)
            return False

    def get_actions(self, actions):
        self.actions = []
        for action in actions:
            if action[3]:
                for options in action[3]:
                    if options[2]:
                        for a in options[2]:
                            self.actions.append('{0} {1}'.format(action[0], a))
                    else:
                        self.actions.append('{0} {1}'.format(action[0],
                                                             options[1]))
            else:
                self.actions.append(action[0])

    def act(self, action, comment=''):
        action = action.split()
        try:
            name, options = action[0], action[1:]
            actions = trac.server.ticket.getActions(self.current.get('id'))
        except IndexError:
            vim.command("echoerr 'No action requested'")
            return
        except Exception as e:
            print_error(e)
            return
        action = None
        for a in actions:
            if a[0] == name:
                action = a
                break
        else:
            vim.command("echoerr 'action is not valid'")
            return
        attribs = {'action': name}
        for i, opt in enumerate(options):
            ac = action[3][i]
            if opt in ac[2]:
                attribs[ac[0]] = opt
            elif opt == ac[1]:
                attribs[ac[0]] = opt
            else:
                vim.command("echoerr 'invalid option'")
                return
        return self.update(comment, attribs)

    def get_options(self, key='type', type_='attrib'):
        options = {
            'attrib': self.options.get(key, []),
            'field': self.options.keys(),
            'action': self.actions,
            'history': map(str, trac.history['ticket']),
        }.get(type_, [])
        vim.command('let g:tracOptions={0}'.format(options))


def search(search_pattern):
    try:
        a_search = trac.server.search.performSearch(search_pattern)
    except Exception as e:
        return "Error: {0}".format(e)
    result = [
        "Results for {0}".format(search_pattern),
        "(Hit <enter> on a line containing :>>)",
        "",
    ]
    for search in a_search:
        if '/ticket/' in search[0]:
            prefix = "Ticket"
        if '/wiki/' in search[0]:
            prefix = "Wiki"
        if '/changeset/' in search[0]:
            prefix = "Changeset"
        title = '{0}:>> {1}'.format(prefix, os.path.basename(search[0]))
        result.extend([title, search[4], ""])
    return '\n'.join(result)


def timeline(server, on=None, author=None):
    try:
        import feedparser
        from time import strftime
    except ImportError:
        vim.command('echoerr "Please install feedparser.py!"')
        return

    query = 'max={0}&format=rss'.format(vim.eval('tracTimelineMax'))
    if on in ('wiki', 'ticket', 'changeset'):
        query = '{0}=on&{1}'.format(on, query)
    elif not author:
        author = on
    if author:
        query = 'authors={0}&{1}'.format(author, query)
    feed = '{scheme}://{server}/timeline?{q}'.format(q=query, **server)
    d = feedparser.parse(feed)
    str_feed = ["Hit <enter> on a line containing :>>", ""]
    for item in d['items']:
        str_feed.append(strftime("%Y-%m-%d %H:%M:%S", item.updated_parsed))

        if 'ticket' in item.category:
            m = re.match(r'^Ticket #(\d+)', item.title)
            if m:
                str_feed.append('Ticket:>> {0}'.format(m.group(1)))
        if 'wiki' in item.category:
            str_feed.append('Wiki:>> {0}'.format(item.title.split(' ', 1)[0]))
        if 'changeset' in item.category:
            m = re.match(r'^Changeset .*\[(\w+)\]:', item.title)
            if m:
                str_feed.append('Changeset:>> {0}'.format(m.group(1)))

        str_feed.append(item.title)
        if item.get('author'):
            str_feed.append(u'Author: {0}'.format(item.author))
        str_feed.append(u'Link: {0}'.format(item.link))
        str_feed.append('')

    return '\n'.join(str_feed)


class Trac(object):
    BASIC_AUTH = 'basic'
    DIGEST_AUTH = 'digest'
    USER_AGENT = "Vitra 1.2 (Trac client for Vim)"

    def __init__(self):
        self.wiki = Wiki()
        self.ticket = Ticket()

        self.uiwiki = WikiUI()
        self.uiticket = TicketUI()

        self.server_window = ServerWindow(prefix='Trac', name='Servers')
        self.timeline_window = TimelineWindow(prefix='Timeline')

        self.default_comment = vim.eval('tracDefaultComment')
        self.server = vim.eval('tracDefaultServer')
        self.history = {'wiki': [], 'ticket': []}

    @property
    def wiki_content(self):
        return self.uiwiki.windows['wiki'].content

    @property
    def ticket_content(self):
        return self.uiticket.windows['edit'].content

    @property
    def server(self):
        return self._server

    @server.setter
    def server(self, server):
        self.clear()
        server_list = vim.eval('tracServerList')
        if not server:
            server = server_list.keys()[0]
        url = server_list[server]
        self.server_name = server
        self.server_url = {
            'scheme': url.get('scheme', 'http'),
            'server': url['server'],
            'rpc_path': url.get('rpc_path', '/login/rpc'),
            'auth': url.get('auth', ''),
            'auth_type': url.get('auth_type', self.BASIC_AUTH),
        }
        auth = self.server_url['auth'].split(':')
        auth_type = self.server_url['auth_type']

        if auth_type == self.BASIC_AUTH:
            url = '{scheme}://{auth}@{server}{rpc_path}'
            transport = None
        elif auth_type == self.DIGEST_AUTH:
            url = '{scheme}://{server}{rpc_path}'
            transport = HTTPDigestTransport(self.server_url['scheme'], *auth)
        else:
            print_error('Authentication method {0} '
                        'is not supported yet'.format(auth_type))
            return
        self._server = xmlrpclib.ServerProxy(url.format(**self.server_url),
                                            transport=transport)
        self._server.__transport.user_agent = self.USER_AGENT

    def clear(self):
        self.wiki.initialise()
        self.ticket.initialise()
        self.uiwiki.destroy()
        self.uiticket.destroy()

    def set_history(self, type_, page):
        if page and page not in self.history[type_]:
            self.history[type_].append(page)

    def traverse_history(self, type_, current, direction):
        if not all([current, direction, self.history.get(type_)]):
            return current
        loc = self.history[type_].index(current)
        try:
            page = self.history[type_][loc + direction]
        except IndexError:
            page = self.history[type_][0]
        return page

    def wiki_view(self, page=False, direction=None):
        page = page if page else self.wiki.current.get('name', 'WikiStart')
        page = self.traverse_history('wiki', page, direction)

        contents = {
            'wiki': self.wiki.get(page),
            'attachment': '\n'.join(self.wiki.attachments),
        }
        titles = {'wiki': page.replace(' ', '_')}
        if vim.eval('tracWikiToC') == '1':
            contents['list'] = '\n'.join(self.wiki.get_all())

        self.uiwiki.create()
        self.uiwiki.update(contents, titles)
        if vim.eval('tracWikiPreview') == '1':
            self.uiwiki.windows['preview'].load(self.wiki.get_html())
        self.uiwiki.focus('wiki')
        self.set_history('wiki', page)

    def ticket_view(self, tid=None, direction=None):
        try:
            tid = int(tid) if tid else self.ticket.current.get('id')
            tid = self.traverse_history('ticket', tid, direction)
        except (ValueError, TypeError):
            print 'Please provide a valid ticket id'
            return

        self.ticket.get_fields()
        contents = {
            'ticket': self.ticket.get(tid),
            'edit': '',
            'attachment': '\n'.join(self.ticket.attachments),
        }
        titles = {'ticket': '\#{0}'.format(tid)}
        if vim.eval('tracTicketStyle') == 'full':
            contents['list'] = self.ticket.get_all()
            titles['list'] = 'Page\ {0}\ of\ {1}'.format(self.ticket.page,
                                                    self.ticket.total_pages)
        self.uiticket.create()
        self.uiticket.update(contents, titles)
        if tid:
            self.uiticket.focus('ticket')
            if vim.eval('tracTicketFormat') == '1':
                try:
                    self.uiticket.windows['ticket'].load(contents['ticket'])
                except Exception as e:
                    print 'Could not format the content'
                    print_error(e)
        self.set_history('ticket', tid)

    def timeline_view(self, on=None, author=None):
        self.timeline_window.write(timeline(self.server_url, on, author))
        self.timeline_window.set_name(self.server_name)

    def server_view(self):
        server_list = vim.eval('tracServerList')
        default = '{0}: '.format(vim.eval('tracDefaultServer'))
        current = '{0}: '.format(self.server_name)
        servers = '\n'.join(['{0}: {1}'.format(key, val['server']) for key, val
                             in server_list.iteritems()])
        if len(default) > 2:
            servers = servers.replace(default, '*{0}'.format(default))
        servers = servers.replace(current, '!{0}'.format(current))
        self.server_window.write(servers)

    def search_view(self, keyword):
        search_window = SearchWindow(name=keyword.replace(' ', '_'),
                prefix='Search\ ({0})'.format(self.server_name))
        search_window.write(search(keyword))

    def changeset_view(self, changeset):
        cs_url = '{scheme}://{server}/changeset/{changeset}'.format(
                changeset=changeset, **self.server_url)
        changeset_window = ChangesetWindow(name=changeset,
                prefix='Changeset\ ({0})'.format(self.server_name))
        changeset_window.load(cs_url)

    def sort_ticket(self, sorter, attr):
        self.ticket.set_sort_attr(sorter, attr)
        self.ticket_view()

    def filter_ticket(self, attrib, value, ignore=False):
        self.ticket.filters[attrib] = '{0}{1}'.format('!' if ignore else '',
                                                      value)
        self.ticket_view()

    def ignore_ticket(self, attrib, value):
        self.filter_ticket(attrib, value, True)

    def filter_clear(self, attrib=None):
        if attrib:
            del self.ticket.filters[attrib]
        else:
            self.ticket.filters = {}
        self.ticket_view()

    def ticket_paginate(self, direction=1):
        try:
            self.ticket.page += direction
            self.ticket_view()
        except:
            self.ticket.page -= direction
            vim.command("echoerr 'cannot go beyond current page'")

    def create_ticket(self, type_=False, summary='new ticket'):
        description = self.ticket_content
        if not description:
            print "Description is empty. Ticket needs more info"
            return

        if not confirm('Create ticket at {0}?'.format(self.server_name)):
            print 'Ticket creation cancelled.'
            return

        attribs = {'type': type_} if type_ else {}
        tid = self.ticket.create(description, summary, attribs)
        if tid is not None:
            self.ticket_view(tid)

    def update_ticket(self, option, value=None):
        text = self.ticket_content
        if option in ('summary', 'description'):
            value = text
            comment = ''
        else:
            comment = text
        attribs = {option: value} if value else {}
        if not any((comment, attribs)):
            print 'nothing to change'
            return
        tid = self.ticket.current['id']
        if not confirm('Update ticket #{0}?'.format(tid)):
            print 'Update cancelled.'
            return False
        if self.ticket.update(comment, attribs, False):
            self.ticket_view()

    def act_ticket(self, action):
        if self.ticket.act(action, self.ticket_content):
            self.ticket_view()

    def save_wiki(self, comment):
        if self.wiki.save(comment):
            self.wiki_view()

    def open_line(self):
        line = vim.current.line
        if 'Ticket:>>' in line:
            vim.command('tabnew')
            self.ticket_view(line.replace('Ticket:>> ', '').strip())
        elif 'Wiki:>>' in line:
            vim.command('tabnew')
            self.wiki_view(line.replace('Wiki:>> ', '').strip())
        elif 'Changeset:>>' in line:
            self.changeset_view(line.replace('Changeset:>> ', '').strip())
        elif line.startswith('Link: '):
            webbrowser.open(line.replace('Link: ', ''))

    def add_attachment(self, file):
        bname = vim.eval("expand('%', ':.')")
        if bname.startswith('Wiki: '):
            print "Adding attachment to wiki", self.wiki.current.get('name')
            if self.wiki.add_attachment(file):
                self.wiki_view()
                print 'Done.'
        elif bname.startswith('Ticket: '):
            print "Adding attachment to ticket", self.ticket.current.get('id')
            comment = self.ticket_content
            if self.ticket.add_attachment(file, comment):
                self.ticket_view()
                print 'Done.'
        else:
            print "You need an active ticket or wiki open!"

    def get_attachment(self, file):
        bname = vim.eval("expand('%', ':.')")
        if bname.startswith('Wiki: '):
            print "Retrieving attachment from wiki",
            print self.wiki.current.get('name')
            if self.wiki.get_attachment(file):
                print 'Done.'
        elif bname.startswith('Ticket: '):
            print "Retrieving attachment from ticket",
            print self.ticket.current.get('id')
            if self.ticket.get_attachment(file):
                print 'Done.'
        else:
            print "You need an active ticket or wiki open!"

    def load_current(self, text_for):
        text = self.ticket.current.get(text_for)
        self.uiticket.update({'edit': text}, {})

    def preview(self):
        bname = vim.eval("expand('%', ':.')")
        if bname.startswith('Wiki: '):
            wikitext = self.wiki_content
        elif bname.startswith('Ticket: '):
            wikitext = self.ticket_content
        else:
            print "You need an active ticket or wiki open!"
            return

        try:
            file_name = save_html(self.server.wiki.wikiToHtml(wikitext))
            webbrowser.open('file://{0}'.format(file_name))
        except Exception as e:
            print_error(e)

    def back(self, forward=False):
        direction = 1 if forward else -1
        bname = vim.eval("expand('%', ':.')")
        if bname.startswith('Wiki: '):
            self.wiki_view(direction=direction)
        elif bname.startswith('Ticket: '):
            self.ticket_view(direction=direction)
        else:
            print "You need an active ticket or wiki open!"
            return


def trac_init():
    global trac
    trac = Trac()
