import sys

from parse_rose_app_conf import RoseAppParser

def main(filename):
    rapper = RoseAppParser()
    rapper.parse(filename)

    max_name_len = 0
    for streq in rapper.streq_list:
        max_name_len = max(max_name_len, len(streq.name))
    for streq in rapper.streq_list:
        fmt = '{{0: >3}} {{1: >3}} {{2: >{}}} {{3: >10}} {{4: >10}}'.format(max_name_len)
        print(fmt.format(streq.isec,
                         streq.item,
                         streq.name,
                         streq.domain.dom_name,
                         streq.time.tim_name))
              

if __name__ == '__main__':
    main(sys.argv[1])
