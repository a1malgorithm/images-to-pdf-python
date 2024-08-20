import os
from tkinter import Tk, Button, Label, filedialog
from PIL import Image

def select_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        folder_label.config(text=folder_path)
        convert_images_to_pdf(folder_path)

def convert_images_to_pdf(folder_path):
    # List to store images
    image_list = []

    # Loop through all files in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith(('jpg', 'jpeg', 'png', 'jfif')):
            file_path = os.path.join(folder_path, file_name)
            image = Image.open(file_path)
            # Convert all images to RGB mode
            image = image.convert('RGB')
            image_list.append(image)

    if image_list:
        # Save all images to a single PDF file
        pdf_path = os.path.join(folder_path, "output.pdf")
        image_list[0].save(pdf_path, save_all=True, append_images=image_list[1:])
        status_label.config(text=f"PDF saved to {pdf_path}")
    else:
        status_label.config(text="No images found in the selected folder")

# Set up the GUI
root = Tk()
root.title("Image to PDF Converter")

select_button = Button(root, text="Select Folder", command=select_folder)
select_button.pack(pady=20)

folder_label = Label(root, text="No folder selected")
folder_label.pack(pady=10)

status_label = Label(root, text="")
status_label.pack(pady=10)

root.mainloop()
