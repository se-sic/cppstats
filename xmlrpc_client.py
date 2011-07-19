#!/usr/bin/python

import xmlrpclib

sp = xmlrpclib.ServerProxy('http://troi:10001/')
print(sp.system.listMethods())
print('1', sp.checkEquivalence('&not (p &and q)', '(&not p &or &not q)'))
print('2', sp.checkEquivalence('(VIM__H &and MACOS &and (__POWERPC__ &or MACOS_X &or __fourbyteints__ &or __MRC__ &or __SC__ &or __APPLE_CC__))', '(SASC) &and (SASC < 658)'))
print('3', sp.checkEquivalence('(BUF = 32) &and MSWIN', 'MSWIN'))
print('4', sp.checkEquivalence('((VIMssH &and MACOS) &and (ssPOWERPCss &or MACOS_X &or ssfourbyteintsss &or ssMRCss &or ssSCss &or ssAPPLE_CCss))', '(SASC) &and (SASC < 658)'))
