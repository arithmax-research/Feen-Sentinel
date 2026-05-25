# Initialize a map object.
import geemap.core as geemap
import ee
ee.Authenticate()
ee.Initialize(project='algorithmictrading-414808')

m = geemap.Map()

# Define an example image.
img = ee.Image.random()

# Add the image to the map.
m.add_layer(img, None, 'Random image')

# Display the map (you can call the object directly if it is the final line).
display(m)