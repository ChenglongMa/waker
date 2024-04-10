from PIL import Image
import cairosvg

# Convert SVG to PNG with specified size
cairosvg.svg2png(url='src/waker/assets/icon.svg', write_to='icon.png')#, output_width=256, output_height=256)

# Open the PNG file
img = Image.open('icon.png')

# Resize the image to the desired size
# img = img.resize((256, 256), Image.Resampling.LANCZOS)

# Save as ICO file with specified size
img.save('src/waker/assets/icon.ico', format='ICO', sizes=[(256, 256)])
# img.save('src/waker/assets/icon.ico', format='ICO', sizes=[(256, 256)])