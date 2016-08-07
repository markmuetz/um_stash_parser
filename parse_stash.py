from collections import OrderedDict

def load_stash_vars():
    with open('files/vn10.5/STASHmaster_A') as f:
	lines = f.readlines()
    stash_vars = OrderedDict()
    for name_line in [l for l in lines if l[0] == '1']:
	split_line = [s.strip() for s in name_line.split('|')]
	section = int(split_line[2])
	if section not in stash_vars:
	    stash_vars[section] = OrderedDict()
	item = int(split_line[3])
	name = split_line[4]
	stash_vars[section][item] = name
    return stash_vars
    

if __name__ == '__main__':
    stash_vars = load_stash_vars()
