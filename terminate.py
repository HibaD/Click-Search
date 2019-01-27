import boto.ec2
import sys
import time

if len(sys.argv) != 2:
	print "Incorrect number of arguments passed"
	print "Correct format:\n python terminate.py <instance_id>"
	sys.exit()

instance_id = sys.argv[1]
print 'The instance id entered was: ', instance_id

try:
	with open('credentials.csv', 'r') as f:
		lines = f.readlines()
except Exception as exception:
	print exception
	sys.exit()

print "Getting AWS credentials"
user_info_all = lines[1].split(',')
access_key_id = user_info_all[2].strip()
secret_access_key = user_info_all[3].strip()

#connect
conn = boto.ec2.connect_to_region("us-east-2", aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)

instance = conn.terminate_instances(instance_id.split())

if instance[0].id == instance_id:
	print "The instance %s was terminated successfully"%(instance[0].id)
else:
	print "Could not terminate instance provided"
