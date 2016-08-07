from StringIO import StringIO
from collections import namedtuple, OrderedDict
from ConfigParser import ConfigParser

from parse_stash import load_stash_vars

class DisabledValue(object):
    def __init__(self, value):
        self.value = value


class Node(object):
    def __init__(self, id):
        self.id = id
        self.keys = OrderedDict()


    def _add_keys(self, key_names):
        for key in key_names:
            self._add_key(key)


    def _add_key(self, key):
        self.keys[key] = None


    def set(self, key, value, disabled):
        if key not in self.keys:
            raise ValueError('key {} not in keys'.format(key))
        self.keys[key] = (disabled, value)


    def get(self, key):
        disabled, value = self.keys[key]
        if not disabled:
            return value
        else:
            return DisabledValue(value)


    def __getattr__(self, key):
        return self.get(key)


    def __repr__(self):
        return '<{} ({})>'.format(self.__class__.__name__, self.id)


class StashReq(Node):
    def __init__(self, id):
        super(StashReq, self).__init__(id)
        key_names = ['dom_name', 'isec', 'item', 'package', 'tim_name', 'use_name']
        self._add_keys(key_names)


class Time(Node):
    def __init__(self, id):
        super(Time, self).__init__(id)
        key_names = ['iedt', 'iend', 'ifre', 'intv', 'ioff', 'iopt', 'isam', 
                     'isdt', 'iser', 'istr', 'itimes', 'ityp', 'lts0', 
                     'tim_name', 'unt1', 'unt2', 'unt3']
        self._add_keys(key_names)
        self.streqs = []


class Use(Node):
    def __init__(self, id):
        super(Use, self).__init__(id)
        key_names = ['file_id', 'locn', 'macrotag', 'use_name']
        self._add_keys(key_names)
        self.streqs = []


class Domain(Node):
    def __init__(self, id):
        super(Domain, self).__init__(id)
        key_names = ['dom_name', 'iest', 'ilevs', 'imn', 'imsk', 'inth', 'iopa', 
                     'iopl', 'isth', 'iwst', 'iwt', 'levb', 'levlst', 'levt', 
                     'plt', 'pslist', 'rlevlst', 'tblim', 'tblimr', 'telim', 
                     'tnlim', 'ts', 'tslim', 'tsnum', 'ttlim', 'ttlimr', 'twlim']
        self._add_keys(key_names)
        self.streqs = []


class RoseAppParser(object):
    def parse(self, filename):
        self._cp = ConfigParser()
        # Preserve case of options.
        self._cp.optionxform = str

        # Skip first two lines (contains meta info that confuses cp).
        with open(filename) as f:
            meta_info = f.readline()
            assert(meta_info[:4] == 'meta')
            meta_value = meta_info.split('=')[1].strip()
            self.um_module, self.um_version = meta_value.split('/')

            assert(f.readline()[0] == '\n')
            ra = self._cp.readfp(f)

        # Build up list of names for each node type from file.
        stash_names = [s for s in self._cp.sections() if s[:14] == 'namelist:streq']
        time_names = [s for s in self._cp.sections() if s[:13] == 'namelist:time']
        use_names = [s for s in self._cp.sections() if s[:12] == 'namelist:use']
        dom_names = [s for s in self._cp.sections() if s[:15] == 'namelist:domain']

        # Build node objects from representations in file.
        self.streq_list = self._parse_node_list(stash_names, StashReq)
        self.time_list = self._parse_node_list(time_names, Time)
        self.use_list = self._parse_node_list(use_names, Use)
        self.domain_list = self._parse_node_list(dom_names, Domain)

        # Build easy access dicts for time, use and domain.
        self.time_dict = self._build_dict(self.time_list, 'tim_name')
        self.use_dict = self._build_dict(self.use_list, 'use_name')
        self.domain_dict = self._build_dict(self.domain_list, 'dom_name')

        # There can be multiple streqs with the same section/item key.
        self.streq_dict = OrderedDict()
        for streq in self.streq_list:
            if int(streq.isec) not in self.streq_dict:
                self.streq_dict[int(streq.isec)] = OrderedDict()

            if int(streq.item) in self.streq_dict[int(streq.isec)]:
                self.streq_dict[int(streq.isec)][int(streq.item)].append(streq)
            else:
                self.streq_dict[int(streq.isec)][int(streq.item)] = [streq]

        # Hook up nodes together.
        self._build_links()

        # Use stash_vars to work out full names for each streq.
        self._add_full_stash_names()


    def remove_streq(self, streq):
        self.streq_list.remove(streq)
        self.streq_dict[int(streq.isec)].pop(int(streq.item))
        self._cp.remove_section(streq.id)


    def remove_domain(self, dom_name):
        if dom_name not in self.domain_dict:
            raise ValueError('{} not a domain'.format(dom_name))
        domain = self.domain_dict[dom_name]
        for streq in domain.streqs:
            self.remove_streq(streq)
        self.domain_list.remove(domain)
        self.domain_dict.pop(domain.dom_name)
        self._cp.remove_section(domain.id)


    def remove_time(self, tim_name):
        if tim_name not in self.time_dict:
            raise ValueError('{} not a time'.format(tim_name))
        time = self.time_dict[tim_name]
        for streq in time.streqs:
            self.remove_streq(streq)
        self.time_list.remove(time)
        self.time_dict.pop(time.tim_name)
        self._cp.remove_section(time.id)


    def remove_use(self, use_name):
        if use_name not in self.use_dict:
            raise ValueError('{} not a use'.format(use_name))
        use = self.use_dict[use_name]
        for streq in use.streqs:
            self.remove_streq(streq)
        self.use_list.remove(use)
        self.use_dict.pop(use.use_name)
        self._cp.remove_section(use.id)


    def write(self, filename):
        # Write to StringIO so that can perform replace on ' = '.
        sio = StringIO()
        sio.write('meta={}/{}\n\n'.format(self.um_module, self.um_version))
        self._cp.write(sio)
        sio.seek(0)
        with open(filename, 'w') as f:
            f.writelines([l.replace(' = ', '=') for l in sio.readlines()])


    def _add_full_stash_names(self):
        stash_vars = load_stash_vars()

        for streq in self.streq_list:
            section, item = streq.get('isec'), streq.get('item')
            streq.name = stash_vars[int(section)][int(item)]


    def _build_links(self):
        for streq in self.streq_list:
            streq.domain = self.domain_dict[streq.get('dom_name')]
            streq.domain.streqs.append(streq)

            streq.time = self.time_dict[streq.get('tim_name')]
            streq.time.streqs.append(streq)

            streq.use = self.use_dict[streq.get('use_name')]
            streq.use.streqs.append(streq)


    def _build_dict(self, nodes, value):
        node_dict = OrderedDict()
        for node in nodes:
            node_dict[node.get(value)] = node
        return node_dict
        

    def _parse_node_list(self, node_names, node_class):
        node_list = []
        for node_name in node_names:
            node = node_class(node_name)
            opts = self._cp.options(node_name)
            for opt in opts:
                disabled = True if opt[:2] == '!!' else False
                name = opt[2:] if disabled else opt
                value = self._cp.get(node_name, opt)
                value = value.replace("'", "")

                node.set(name, value, disabled)
            node_list.append(node)
        return node_list


if __name__ == '__main__':
    rapper = RoseAppParser()
    rapper.parse('test_confs/init_rose-app.conf')
