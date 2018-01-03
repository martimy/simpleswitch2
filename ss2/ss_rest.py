# Copyright (c) 2016 Noviflow
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy,
# modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
SimpleSwitch 2.0 (SS2) Core Controller Application

Modified to support REST interface
"""

import json
from core import SS2Core
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib import dpid as dpid_lib
from webob import Response

#import config, util, logging
#from ryu.base import app_manager
#from ryu.controller import ofp_event
#from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
#from ryu.controller.handler import set_ev_cls
#from ryu.lib.packet import ethernet, ether_types as ether, packet
from ryu.ofproto import ofproto_v1_3
from ryu.controller import dpset

#from util import kill_on_exception

switch_instance_name = 'switch_api_app'
url = '/ryuswitch/{dpid}'
urlclear = '/ryuswitch/clear/{dpid}'

class SS2REST(SS2Core):
    # A list of supported OpenFlow versions for this RyuApp.
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
                    
    # This a dictionary of contexts which this Ryu application wants to use. 
    # The key is a name of context and its value is a class that implements the context.
    # The class is instantiated by app_manager and the instance is shared among RyuApp 
    # subclasses which has _CONTEXTS member with the same key. 
    # A RyuApp subclass can obtain a reference to the instance via its __init__'s kwargs.
    _CONTEXTS = {'dpset': dpset.DPSet,
                  'wsgi': WSGIApplication}
    
    dplist = {}
    
    def __init__(self, *args, **kwargs):
        super(SS2REST, self).__init__(*args, **kwargs)

        wsgi = kwargs['wsgi']
        self.dpset = kwargs['dpset']
        self.data = {}
        self.data['dpset'] = self.dpset
        self.data[switch_instance_name] = self
        # Registers the controller class 
        wsgi.register(RyuSwitchController, self.data) #{switch_instance_name: self})
        # The register method calls the following line
        # wsgi.registory['StatsController'] = self.data
        
    def add_datapath(self, dp):
        self.dplist.setdefault(dp.id, dp)
        print(self.dplist)
        return super(SS2REST, self).add_datapath(dp)
        

class RyuSwitchController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(RyuSwitchController, self).__init__(req, link, data, **config)
        self.switch = data[switch_instance_name] # passed in the registration
        self.dpset = data['dpset']
        
        
    @route('anyname', url, methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def list_mac_table(self, req, **kwargs):

        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])


        body = json.dumps({"dpid": dpid})
        return Response(content_type='application/json', body=body)
        
    @route('anyname', urlclear, methods=['PUT'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def put_mac_table(self, req, **kwargs):

        dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        print(self.dpset.get_all())
        
        try:
            new_entry = req.json if req.body else {}
        except ValueError:
            raise Response(status=400)

        #if dpid not in self.dpset.get_all():
        #    return Response(status=404)

        try:
            dp = self.dpset.get(dpid)
            msgs = self.reset_flows(dp)
            for msg in msgs:
                dp.send_msg(msg)
            
            body = json.dumps(new_entry)
            return Response(content_type='application/json', body=body)
        except Exception as e:
            print(e)
            return Response(status=500)
            
    def reset_flows(self, dp):
        "Add the specified datapath to our app by adding default rules"
        #self.logger.info('Adding datapath %d',dp.id)

        msgs = self.switch.clean_all_flows(dp)
        msgs += self.switch.add_default_flows(dp)
        return msgs

