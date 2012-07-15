# `Vitra` (Trac UI for ViM)

[`Vitra`][vitra] is a [Trac][Trac] client UI for the wonderful universal editor
[Vim][Vim]. It talks to a trac server via XML-RPC.  It provides a fancy UI for
both wiki and tickets. A paginated list of tickets window, full ticket detail
window along with attachment window makes a great UI for ticket manipulation.
The wiki UI combines the list of wiki pages, edit window with the content of
the wiki and a preview window. It also has timeline, search and changeset
windows.

# Screenshots

Ticket UI

![django tickets][djtkt]

Wiki UI

![django wiki][djwiki]

Other windows

![localdj windows][otherwins]

# Requirements

`Vitra` requires Vim 7.3+ to be compiled with python 2.6+. [`Align`][Align] and
[`TracWiki`][TWk] are two (optional) vim plugins that makes `Vitra` more
beautiful. Also the trac server should be 0.12+, as it uses the action command
for the workflow rather than just setting resolution on a ticket manually.

# Installation

The preferred way to install `Vitra` is using [`Vundle`][Vundle] or
[`Pathogen`][Pathogen].

## Vundle

Add the following line to your __.vimrc__

    Bundle "nsmgr8/vitra"

Run __:BundleInstall__ in your vim command line.

## Pathogen

To install in a pathogen managed plugins environment follow the steps as

    $ cd ~./vim/bundle
    $ git clone git://github.com/nsmgr8/vitra

Then restart your vim.

## Manual

To install `Vitra` manually in your local vim runtime path, do the following:

    $ git clone git://github.com/nsmgr8/vitra
    $ cp -R vitra/* ~/.vim/

Then restart vim and build the help tags via the vim command line

    :helptags ~/.vim/doc

# Settings

The minimum setting requirement is to define the trac server. One or more trac
server(s) can be defined for use. To add a trac server define the global
dictionary of servers _g:tracServerList_ in your __.vimrc__. Following is an
example of django trac server:

    let g:tracServerList = {}
    let g:tracServerList['djangoproject'] = {
        \ 'scheme': 'https',
        \ 'auth': 'USERNAME:PASSWORD',
        \ 'server': 'code.djangoproject.com',
        \ 'rpc_path': '/login/xmlrpc'
        \ 'auth_type': 'basic',
        \ }

By default, _scheme_ and *rpc_path* have values _http_ and _/login/rpc_.

If you define more than one trac server, you can also choose a default server
that will be selected when a vim session starts. To define the default server
set the _g:tracDefaultServer_ in your .vimrc to the server key of it. e.g.,

    let g:tracDefaultServer = 'djangoproject'

It is also possible to change the trac server in the running vim session. Use
__TracServer__ command to change the trac server to use. It can offer tab
completion for available servers that are defined in _g:tracServerList_. Note
that, this does not set the server to be default for next sessions.

`Vitra` supports __Basic HTTP__, __Digest HTTP__ and __Kerberos__
authentication.

# UI

After the settings, one can open the wiki or ticket interface by __TWOpen__ or
__TTOpen__ command respectively. Both commands can also optionally take a wiki
page name or ticket number to open. If the requested wiki page does not exist,
the wiki edit window will offer the page to be created. In case of non-existent
ticket number, it will show an error in the ticket detail window.

## Ticket UI

The ticket UI consists of four windows, viz., Listing, Detail, Edit and
Attachment windows. The listing window is a paginated list of tickets. One can
paginate through the list via __TTNextPage__ or __TTPreviousPage__ commands.
There are also two handy __TTFirstPage__ and __TTLastPage__ commands which
lists the first and last page of the ticket lists. One can open a ticket from
the listing just by pressing `ENTER` or double-clicking on a line.

A number of __TTFilter*Attr*__, __TTIgnore*Attr*__ commands will be available
to filter the list of tickets by attributes. __TTOrderBy__ and __TTGroupBy__
are also available for sorting the list on ticket attributes, which also have
tab completion values for the ticket attribute keys. Filters can be cleared
individually by __TTClearFilter__ or completely by __TTClearAllFilters__.

The detail window shows the content of the ticket along with changelog. This is
a read only buffer, that is this content is not editable. It lists the current
values of all ticket attributes, description and the conversation with all the
history of attribute changes.

The edit window is an empty writable buffer, where one can create/update a
ticket. To create a new ticket enter the ticket description in this window and
run the command __TTCreate__ following the ticket summary. e.g., enter the
following in the edit window

    Here is the ticket description.

And run the following command

    :TTCreate Summary of the ticket

This will create the ticket on the trac server and load it back in the detail
window.

To update the summary, description or to add a comment, enter the text in the
edit window and run __TTSetSummary__, __TTSetDescription__ or __TTAddComment__
respectively. There are also handy commands to load current summary or
description in the edit window to update them. They are, obviously,
__TTEditSummary__ and __TTEditDescription__.

There will also be a number of __TTUpdate*Attr*__ command available for
updating the respective attributes of the ticket. e.g., __TTUpdateType__ will
update the type of the ticket. It will also offer tab completion to select the
type.

One can also attach a file to the ticket via __TAddAttachment__ command which
also offers tab completion on the file system to find your file to attach. The
attachments are listed in the attachment window. Pressing `ENTER` will download
the file into current folder.

`Vitra` supports the trac workflow actions. It loads a ticket with the actions
available. One can apply the action by __TTAction__, which again offers tab
completion. The action will be verified before applying, so that invalid
actions cannot be applied.

`Vitra` also keeps the history of opened tickets in the current session.
Therefore it is possible to move back/forward from the currently opened ticket.
To navigate the current history one should apply the command __TBack__ or
__TForward__ to go back or forward in the history of opened tickets.

To close the ticket UI, run __TTClose__ command. One can preview an HTML of the
ticket edit window content in the default browser by __TPreview__.

## Wiki UI

Wiki interface also consists of four windows, viz., Listing, Edit, Preview and
Attachment windows. Listing window lists all available wiki pages. One can open
a wiki by pressing `ENTER` or double-clicking a line.

The main wiki window allows the wiki page to be edited. One can edit a wiki
page here and run __TWSave__ to save the changes. To create a new wiki page,
run `TWOpen new_page_name`, enter the text into the wiki window and run
`TWSave`.

Like the ticket attachment window, wiki page also has a corresponding
attachment window. Run __TAddAttachment__ similarly to add a file and press
`ENTER` to retrieve the attachment.

The UI also provides a preview which shows a stripped out html output of the
current wiki page.

__TBack__ and __TForward__ also traverses the history of opened wiki pages as
well.

__TWClose__ can close the wiki UI. Also, __TWInfo__ can print useful
information about the current page. One can locally preview the HTML of the
current wiki page content by __TPreview__.

## Other windows

 * __TTimeline__ opens the timeline in a window and by pressing `ENTER` one can
   open a ticket, wiki or changeset.
 * __TSearch__ command can search the trac and provide a window with the search
   result where one can open a ticket, wiki or changeset by pressing `ENTER`.
 * __TChangeset__ command can open a diff view of a given changeset in
   a window.
 * __TServer__ opens a buffer with a list of available servers. By pressing
   `ENTER` one can switch server.

# Options

The following options are available for `Vitra`:

 * _g:tracDefaultServer_:  ''
   * Set your preferred trac server, if you have more than one defined in
     _g:tracServerList_.
 * _g:tracDefaultComment_: 'Updated from Vitra'
   * Default comment to use when saving changes to trac.
 * _g:tracTicketClause_: 'status!=closed'
   * This provides a default filtering options for ticket listing.
 * _g:tracTicketGroup_: 'milestone'
   * Set to your preferred attribute for listing tickets in groups.
 * _g:tracTicketOrder_: 'priority'
   * Set to your preferred attribute for listing tickets in order.
 * _g:tracTicketStyle_: 'full'
   * Unless set to 'full', the ticket listing window will appear in the ticket
     UI. Also this will hide all other buffers other than the ticket UI.
 * _g:tracTicketFormat_: 1
   * If set to 1, show formatted text in ticket detail window. Otherwise, show
     the wiki markup content.
 * _g:tracWikiStyle_: 'full'
   * If set to 'full', the wiki UI will hide all other buffers.
 * _g:tracWikiPreview_: 1
   * If set to 1, the wiki UI will show a preview of the current page.
 * _g:tracWikiToC_: 1
   * If set to 1, the wiki UI will show the list of available pages.
 * _g:tracHideTracWiki_: 1
   * If set to 1, the list of wiki pages will not show the Trac's own pages.
 * _g:tracTimelineMax_: 50
   * Number of maximum number of entries to get in the timeline.

# Links

 * [Homepage][vitra]
 * [Vim scripts][vimscripts]
 * [Development][development]
 * [Issues/Bug Reports][issues]

# Inspiration

This plugin is inspired by the the other trac vim integration plugin
[`Trac.vim`][vimtrac] available for years.

# License

The source code is licensed under MIT license. Please hack it to suit yourself.

## The MIT License (MIT)

Copyright (c) 2011 M. Nasimul Haque

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[vitra]: http://nsmgr8.github.com/vitra/ "Vitra"
[Vim]: http://www.vim.org/ "Vim"
[Trac]: http://trac.edgewall.org/ "Trac"
[Align]: http://www.vim.org/scripts/script.php?script_id=294 "Align plugin"
[TWk]: http://www.vim.org/scripts/script.php?script_id=3337 "Trac wiki syntax"
[Vundle]: https://github.com/gmarik/vundle "Vim plugin manager"
[Pathogen]: http://github.com/tpope/vim-pathogen "Vim runtime manager"
[djtkt]: http://dl.dropbox.com/u/125015/vitradjangotickets.png "Django tickets"
[djwiki]: http://dl.dropbox.com/u/125015/vitradjangowiki.png "Django wiki"
[otherwins]: http://dl.dropbox.com/u/125015/vitraothers.png "Other windows"
[vimtrac]: http://www.vim.org/scripts/script.php?script_id=2147
[vimscripts]: http://www.vim.org/scripts/script.php?script_id=4092
[development]: https://github.com/nsmgr8/vitra "github"
[issues]: https://github.com/nsmgr8/vitra/issues "issues, bug reports"
