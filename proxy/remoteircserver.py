
import time
from itertools import imap

from eventlist import EventList
from errors import ServerError

SERVER_COMMANDS = [
    "action",
    "admin",
    "ctcp",
    "ctcp_reply",
    "globopts",
    "info",
    "invite",
    "ison",
    "join",
    "kick",
    "links",
    "list",
    "lusers",
    "mode",
    "motd",
    "names",
    "nick",
    "notice",
    "oper",
    "part",
    "pass",
    "ping",
    "pong",
    "privmsg",
    "privmsg_many",
    "quit",
    "squit",
    "stats",
    "time",
    "topic",
    "trace",
    "user",
    "userhost",
    "users",
    "version",
    "wallops",
    "who",
    "whois",
    "whowas",
]

class RemoteIRCServer(object):
    '''Represents an IRC Server that the client has connected to.

    Any method that does not start with an underscore is served via XMLRPC
    under the name server_<method>.

    '''

    def __init__(self, connection, server_name, nick_name, uri, port, password=None,
        ssl=False, ipv6=False):

        self.connection = connection
        self.server_name = server_name
        self.nick_name = nick_name
        self.uri = uri
        self.port = port

        self.connection.connect(uri, port, nick_name, password,
            ssl, ipv6)

        self.channels = {}
        self.events = EventList()

    def _handle_irc_event(self, event):
        '''Callback for events from IRC belonging to this server.

        Stores the event in the repective channel, or in a server event list if
        the event does not belong to a channel.

        :param event:
            An event dictionary, created in IRCProxyServer._handle_irc_event,
            where this method is called.

        '''

        # Hand event to channel, if applicable
        if event["target"] and event["target"][0] in "#&+!":
            for channel_name, channel in self.channels.iteritems():
                if channel_name == event["target"]:
                    event["channel"] = channel_name
                    channel._handle_irc_event(event)
                    return

        # Event has no channel
        self.events.append(event)

    def _dispatch_channel_method(self, method, params):
        '''Dispatch XMLRPC methods that start with "channel_".

        First, this server instance is searched for the method name including
        the "channel_" prefix.  If that isn't found, the a method name
        (excluding the "channel_") is looked for in RemoteIRCChannel.

        :param method:
            Name of the XMLRPC method requested.

        :param params:
            A tuple of the parameters given in the XMLRPC call.

        :returns:
            The return value of the method that was called.

        '''

        # Method inside this instance
        func = getattr(self, "channel_%s" % method, None)
        if func != None and callable(func):
            return func(*params)

        # Method inside channel object
        # The check to make sure method is not private is done in
        # IRCProxy._dispatch, which calls this function.
        if hasattr(RemoteIRCChannel, method) and len(params) > 0:
            channel = self.channels[params[0]]
            func = getattr(channel, method, None)
            if func != None and callable(func):
                return func(*params[1:])

        raise ServerError('Proxy server does not support method "channel_%s".' % method)

    def _disconnect(self, leave_message=""):
        '''Disconnect from this server.

        :param leave_message:
            A message that is given to each channel and the server when
            leaving.

        '''
        for channel in self.channels:
            channel.leave(leave_message)
        self.connection.disconnect(leave_message)

    def channel_join(self, channel_name):
        '''Join a channel.

        :param channel_name:
            Name of the channel to join.

        '''
        channel = RemoteIRCChannel(self, channel_name)
        self.channels[channel_name] = channel
        self.events.append(type="channel_join", channel=channel_name)
        return True

    def channel_list(self):
        '''List channels in this server that the user is currently in.

        :returns:
            A list of channels.

        '''
        return self.channels.keys()

    def channel_leave(self, channel_name, message=""):
        '''Leave a channel.

        :param channel_name:
            The name of the channel to join.

        :param message:
            A message that is given to the channel when leaving.

        '''
        channel = self.channels[channel_name]
        channel._leave()
        del channels[channel_name]
        self.events.append(type="channel_leave", channel=channel_name,
                           message=message)
        return True

    #XXX
    '''
    def _get_channel_event_slice(self, start_index, end_index):
        channel_events = imap(lambda x: x.get_event_slice(start_index,
                              end_index), self.channels)
        return reduce(lambda x,y: x+y, channel_events)

    def _get_channel_events_since(self, start_time):
        channel_events = imap(lambda x: x.get_events_since(start_index),
                              self.channels)
        return reduce(lambda x,y: x+y, channel_events)

    def _get_event_slice(self, start_index, end_index):
        return self.events.get_event_slice(start_index, end_index)
    '''

    def _get_events_since(self, start_time):
        events = self.events.get_events_since(start_time)
        for channel in self.channels.itervalues():
            events.extend(channel._get_events_since(start_time))
        return events

class RemoteIRCChannel(object):
    '''Represents a channel on an RemoteIRCServer.

    Any method that does not start with an underscore is served via XMLRPC
    under the name channel_<method>.

    '''

    def __init__(self, server, channel_name):
        self.server = server
        self.channel_name = channel_name

        self.server.connection.join(self.channel_name)
        self.events = EventList()

    def _handle_irc_event(self, event):
        self.events.append(event)

    def _leave(self, message):
        self.server.connection.part(channel_name, message)

    #XXX
    '''
    def get_event_slice(self, start_index, end_index):
        return self.events.get_event_slice(start_index, end_index)
    '''

    def _get_events_since(self, start_time):
        return self.events.get_events_since(start_time)

    def message(self, message):
        self.events.append({
            "server": self.server.server_name,
            "type": "privmsg",
            "source": self.server.nick_name,
            "target": self.channel_name,
            "arguments": [message],
            "time": time.time(),
        })
        self.server.connection.privmsg(self.channel_name, message)
        return True
