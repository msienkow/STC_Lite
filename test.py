from pylogix import PLC

comm = PLC()
comm.IPAddress = '10.100.135.43'
comm.Micro800 = True
tags = []
for i in range(8):
    tags.append(f'Analog_In[{i}]')

for i in range(12):
    tags.append(f'Digital_In.{i}')

ret = comm.Read(tags)
comm.Close()


for i in range(len(tags)):
    print(f'{ret[i].TagName}: {ret[i].Value}')