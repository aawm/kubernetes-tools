#!/usr/bin/env python
#coding:utf-8

import os
import sys
import json
import re

#
# 清理一些没有用的pods,自动卸载volum包含有glusterfs的volume
# by Gance/2017-08-28

def  main(argv):
	print("-------PodCleanner Version 2.1" )

	output = os.popen("kubectl get pods -o custom-columns=uid:metadata.uid,name:metadata.name,namespace:metadata.namespace,status:status.phase --all-namespaces=true"   )
	content=output.read()
	arr=content.split("\n")
	n=-1
	dict={}
	print("-------正在检查：" )
	for line in arr:
		if len(line) ==0:
			continue
		n=n+1
		if n==0:
			print("--id\t$$$$$$$$-$$$$-$$$$-$$$$-$$$$$$$$$$$$\tstatus\tnamespace\tname")
			continue
 
		arr=line.split()
		#print("%d,len=%d" % (n,len(arr)) )
		if len(arr[2])>7:
			print("--%d\t%s\t%s\t%s\t%s" % (n,arr[0],arr[3],arr[2],arr[1]) )
		else:
			print("--%d\t%s\t%s\t%s\t\t%s" % (n,arr[0],arr[3],arr[2],arr[1]) )

		dict[arr[0]]=arr[1]+","+arr[2]+","+arr[3]

	if n<=0:
		print("-------找不到任何pod列表!")
		return

	mounted_dict={}
	mounted_fuse_gfs=os.popen("mount |grep fuse.glusterfs").read()
	if len(mounted_fuse_gfs)>0:
		print("-------检查GFS的挂载有效性"  )
		fuse_ay=mounted_fuse_gfs.split("\n")
		for line in fuse_ay:
			line1_ay=line.split(" ")
			if len(line1_ay)>3 and line1_ay[1]=="on" and line1_ay[3]=="type":
				device=line1_ay[0]
				target=line1_ay[2]
				try:
					describe=""
					
					#stat=os.stat(target)
					
					m = re.match(r'/var/lib/kubelet/pods/([0-9a-z]{8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12})/volumes/kubernetes\.io~glusterfs/.*', target)
					if m :
						pod_uid=m.group(1)
						if dict.has_key(pod_uid):
							describe=dict[pod_uid]
							print("%s on %s 正常" % (device,target))
						else:
							print("%s on %s 已不存在!" % (device,target))
							print("请运行: ps -ef|grep %s|grep /usr/sbin/glusterfs |awk '{print $2}'  删除对应的pid" %pod_uid)
							tmp_pid=os.popen("ps -ef|grep %s|grep /usr/sbin/glusterfs|awk 'NR==1{print $2}'" %pod_uid).read()
							print("kill -9 %s " % tmp_pid)
							os.popen("kill -9 %s " % tmp_pid)
						print("uid:%s name:%s" %(pod_uid,describe))
						mounted_dict[pod_uid]=target
					else:
						print("can not match regex")
					
				except OSError,e:
					print("%s on %s 已失效!" % (device,target))
					#/var/lib/kubelet/pods/2f49d5c4-87f4-11e7-910c-02e11af0ff6b/volumes/kubernetes.io~glusterfs/pvc-15586ecc-87f1-11e7-910c-02e11af0ff6b
					
					
	else:
		print("-------所有GFS的挂载都正常！"  )


 	output = os.popen("ls /var/lib/kubelet/pods/")
	content= output.read()
	arr_pods= content.split("\n")
	print("-------需要清理的pod列表：")
	n=0
	umount_i=0
	for line in arr_pods:
		#print("%d=" % n,line)
		
		if len(line) ==0:
			continue
		if dict.has_key(line):
			#print(line," is exist!")
			gfs="/var/lib/kubelet/pods/%s/volumes/kubernetes.io~glusterfs" % line
			if os.path.exists(gfs):
				if mounted_dict.has_key(line):
					#print(line," is mount!",mounted_dict[line])
					pass
				else:
					d=""
					if dict.has_key(line):
						d=dict[line]
					umount_i=umount_i+1
					print(umount_i,line," is no mount! ",d)
			pass
		else:
			n=n+1
			hosts="/var/lib/kubelet/pods/%s/etc-hosts" % line
			name="unknown"
			if os.path.exists(hosts):
				f = open(hosts, 'r')
				try:
					text = f.read()
					lines=text.split("\n")
					end_line=lines[len(lines)-2]
					end_line=end_line.replace("\t"," ")
					name=end_line
					#end_line[1]
				finally:
					f.close()
			path="/var/lib/kubelet/pods/%s/" % line
			#/var/lib/kubelet/pods/d66f1c96-adb0-11e7-83b6-02a32b882560/volumes/kubernetes.io~glusterfs/pvc-3f245cad-8c8f-11e7-863b-02a32bbe5a40
			glusterfs="/var/lib/kubelet/pods/%s/volumes/kubernetes.io~glusterfs" % line
			if os.path.exists(glusterfs):
				sub_dir = os.listdir(glusterfs)
				for d in sub_dir:
					mount_tar=glusterfs+"/"+d
					print("mounted target:",mount_tar)
					mounted=os.popen("mount |grep %s|grep %s" %(line,d) ).read()
					mounted_lines=mounted.split("\n")
					line1=mounted_lines[0]
					line1_ay=line1.split(" ")
					if len(line1_ay)>3 and line1_ay[1]=="on" and line1_ay[3]=="type":
						device=line1_ay[0]
						target=line1_ay[2]
						cmd="umount %s %s" % (device,target)
						print(cmd)
						cmd_out=os.popen(cmd).read()
						print(cmd_out)
			rm_output = os.popen("rm -rf /var/lib/kubelet/pods/%s/" % line).read()
			print("%d" % n , line,name,path,rm_output)

	if n==0:
		print("-------所有的pod都正常,不用清理。" )
	else:
		print("-------本次共清理了%d个pod！" % n )


	


if __name__ == '__main__':
	main(sys.argv)
