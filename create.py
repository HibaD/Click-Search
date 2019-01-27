import boto.ec2
import subprocess
import time
import sys

key_pair_name = 'test'

def create_instance():
	#get credentials from supplied file
	try:
		with open('credentials.csv', 'r') as f:
			lines = f.readlines()
	except Exception as exception:
		print exception
		return null
	
	print "Getting AWS credentials"
	user_info_all = lines[1].split(',')
	access_key_id = user_info_all[2].strip()
	secret_access_key = user_info_all[3].strip()
	
	print "\nEstablishing connection"
	# Establish a new connection
	conn = boto.ec2.connect_to_region("us-east-2", aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)

	print "\nCreating key pair"
	#Create the key_pair if it does not exist already
	try:
		key_pair = conn.create_key_pair(key_pair_name)
		key_pair.save("")
	except Exception as exception:
		print exception
	
	print "\nAdding security group"
	#Create the security group and define rules, if does not already exist
	try:
		group = conn.create_security_group('csc326-group3', 'Instance for lab 4')
	except Exception as exception:
		groups = conn.get_all_security_groups()
		for g in groups:
			if g.name == 'csc326-group3':
				group = g
				print "Group already exists!"
		print exception
	print "\nAdding security rules"
	try:
		group.authorize("icmp", -1, -1, "0.0.0.0/0")
		group.authorize("tcp", 22, 22, "0.0.0.0/0")
		group.authorize("tcp", 80, 80, "0.0.0.0/0")
	except Exception as exception:
		print exception
				
	#Create a running instance
	resp = conn.run_instances('ami-0b59bfac6be064b78',key_name=key_pair_name,instance_type='t2.micro',security_groups=[group])
	inst = resp.instances[0]
	print "\nInstance created/run"

	#wait until instance is running
	while inst.update() != 'running':
		time.sleep(5)
	
	print "\nEnsure server is stable"
	for i in range(60,0,-1):
		time.sleep(1)
		sys.stdout.write(str(i)+' ')
	sys.stdout.flush()
	print "\nServer is now stable.."
	
	print "\nCopying files to server"
	subprocess.call("scp -o StrictHostKeyChecking=no -i %s.pem install.sh ec2-user@%s:~/" % (key_pair_name, inst.public_dns_name), shell=True)
	subprocess.call("scp -o StrictHostKeyChecking=no -i %s.pem csc326.db ec2-user@%s:~/" % (key_pair_name, inst.public_dns_name), shell=True)
	subprocess.call("scp -o StrictHostKeyChecking=no -i %s.pem main.tpl ec2-user@%s:~/" % (key_pair_name, inst.public_dns_name), shell=True)
	subprocess.call("scp -o StrictHostKeyChecking=no -i %s.pem main-anon.tpl ec2-user@%s:~/" % (key_pair_name, inst.public_dns_name), shell=True)
	subprocess.call("scp -o StrictHostKeyChecking=no -i %s.pem styles.tpl ec2-user@%s:~/" % (key_pair_name, inst.public_dns_name), shell=True)
	subprocess.call("scp -o StrictHostKeyChecking=no -i %s.pem error.tpl ec2-user@%s:~/" % (key_pair_name, inst.public_dns_name), shell=True)
	subprocess.call("scp -o StrictHostKeyChecking=no -i %s.pem client_secrets.json ec2-user@%s:~/" % (key_pair_name, inst.public_dns_name), shell=True)
	subprocess.call("scp -o StrictHostKeyChecking=no -i %s.pem server.py ec2-user@%s:~/" % (key_pair_name, inst.public_dns_name), shell=True)
	
	print "Please wait while we launch the server..."
	print "\nConnection Details"
	#Display instance and connection details
	print "Instance ID: %s"%(inst.id)
	print "Instance IP Addresses: %s"%(inst.ip_address)
	print "Instance public DNS name: %s"%(inst.public_dns_name)
	print "Please access the website by typing %s:8080 in your web browser."%(inst.ip_address)
	print "\nOpening server"
	

	subprocess.call(("ssh -o StrictHostKeyChecking=no -i %s.pem ec2-user@%s /bin/bash ~/install.sh" % (key_pair_name, inst.ip_address)).split())
	


create_instance()
