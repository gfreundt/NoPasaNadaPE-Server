import ctypes
import math
from PIL import Image

import img2pdf
import pypdfium2.raw as pdfium


def pdf_to_png(from_path, to_path=None, scale=1):
    """if parameter to_path is given, result of funtion is to save image
    if parameter to_path is not given, return object as PIL image"""

    # Load document
    pdf = pdfium.FPDF_LoadDocument((from_path + "\x00").encode("utf-8"), None)

    # Check page count to make sure it was loaded correctly
    page_count = pdfium.FPDF_GetPageCount(pdf)
    assert page_count >= 1

    # Load the first page and get its dimensions
    page = pdfium.FPDF_LoadPage(pdf, 0)
    width = int(math.ceil(pdfium.FPDF_GetPageWidthF(page)) * scale)
    height = int(math.ceil(pdfium.FPDF_GetPageHeightF(page)) * scale)

    # Create a bitmap
    # (Note, pdfium is faster at rendering transparency if we use BGRA rather than BGRx)
    use_alpha = pdfium.FPDFPage_HasTransparency(page)
    bitmap = pdfium.FPDFBitmap_Create(width, height, int(use_alpha))
    # Fill the whole bitmap with a white background
    # The color is given as a 32-bit integer in ARGB format (8 bits per channel)
    pdfium.FPDFBitmap_FillRect(bitmap, 0, 0, width, height, 0xFFFFFFFF)

    # Store common rendering arguments
    render_args = (
        bitmap,  # the bitmap
        page,  # the page
        # positions and sizes are to be given in pixels and may exceed the bitmap
        0,  # left start position
        0,  # top start position
        width,  # horizontal size
        height,  # vertical size
        0,  # rotation (as constant, not in degrees!)
        pdfium.FPDF_LCD_TEXT
        | pdfium.FPDF_ANNOT,  # rendering flags, combined with binary or
    )

    # Render the page
    pdfium.FPDF_RenderPageBitmap(*render_args)

    # Get a pointer to the first item of the buffer
    buffer_ptr = pdfium.FPDFBitmap_GetBuffer(bitmap)
    # Re-interpret the pointer to encompass the whole buffer
    buffer_ptr = ctypes.cast(
        buffer_ptr, ctypes.POINTER(ctypes.c_ubyte * (width * height * 4))
    )
    # Create a PIL image from the buffer contents
    img = Image.frombuffer(
        "RGBA", (width, height), buffer_ptr.contents, "raw", "BGRA", 0, 1
    )
    # Close all
    pdfium.FPDFBitmap_Destroy(bitmap)
    pdfium.FPDF_ClosePage(page)
    pdfium.FPDF_CloseDocument(pdf)
    # Save it as file or return image object
    if to_path:
        img.save(to_path)
        return None
    else:
        return img


def image_to_pdf(image_bytes, to_path):
    try:
        with open(to_path, "wb") as file:
            file.write(img2pdf.convert(image_bytes.filename))
        return True
    except Exception:
        return ""
