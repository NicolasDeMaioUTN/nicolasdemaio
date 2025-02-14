import h3
lat, lon = -34.6603223648, -58.7181396931
h3_index_python = h3.latlng_to_cell(lat, lon, 14)
print(h3_index_python)
# 8edd68294c82ba7
# 8ec2e3ba6705177