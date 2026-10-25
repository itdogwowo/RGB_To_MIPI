"""Render PDF pages (or crops) to PNG using macOS Quartz/CoreGraphics."""
import sys, os
import Quartz
import CoreFoundation
from Quartz import (CGPDFDocumentCreateWithURL, CGPDFDocumentGetNumberOfPages,
                    CGPDFDocumentGetPage, CGPDFPageGetBoxRect, kCGPDFMediaBox,
                    CGBitmapContextCreate, CGContextDrawPDFPage,
                    CGBitmapContextCreateImage, CGImageDestinationCreateWithURL,
                    CGImageDestinationAddImage, CGImageDestinationFinalize,
                    CGContextSetRGBFillColor, CGContextFillRect, CGContextScaleCTM,
                    CGContextTranslateCTM)

PDF = "C48596_其他接口_SSD2828QN4R_规格书_WJ73954.PDF"

def open_doc(path=PDF):
    b = path.encode()
    url = CoreFoundation.CFURLCreateFromFileSystemRepresentation(None, b, len(b), False)
    return CGPDFDocumentCreateWithURL(url)

def render_page(doc, pageno, dpi=200, crop=None, out="out.png"):
    """crop = (x0, y0, x1, y1) in PDF points with origin at TOP-LEFT of the page."""
    pg = CGPDFDocumentGetPage(doc, pageno)
    box = CGPDFPageGetBoxRect(pg, kCGPDFMediaBox)
    scale = dpi / 72.0
    if crop:
        x0, y0, x1, y1 = crop
    else:
        x0, y0, x1, y1 = 0, 0, box.size.width, box.size.height
    w = int(round((x1 - x0) * scale)); h = int(round((y1 - y0) * scale))
    w = max(w, 1); h = max(h, 1)
    cs = Quartz.CGColorSpaceCreateDeviceRGB()
    ctx = CGBitmapContextCreate(None, w, h, 8, 0, cs, Quartz.kCGImageAlphaPremultipliedLast)
    CGContextSetRGBFillColor(ctx, 1, 1, 1, 1)
    CGContextFillRect(ctx, Quartz.CGRectMake(0, 0, w, h))
    CGContextScaleCTM(ctx, scale, scale)
    # shift so that crop top-left maps to origin; PDF y is bottom-up
    CGContextTranslateCTM(ctx, -x0, -(box.size.height - y1))
    CGContextDrawPDFPage(ctx, pg)
    img = CGBitmapContextCreateImage(ctx)
    ob = out.encode()
    ourl = CoreFoundation.CFURLCreateFromFileSystemRepresentation(None, ob, len(ob), False)
    dest = CGImageDestinationCreateWithURL(ourl, "public.png", 1, None)
    CGImageDestinationAddImage(dest, img, None)
    ok = CGImageDestinationFinalize(dest)
    return ok, (w, h)

if __name__ == "__main__":
    doc = open_doc()
    for spec in sys.argv[1:]:
        pageno, out = spec.split(":")
        ok, size = render_page(doc, int(pageno), dpi=110, out=out)
        print(out, ok, size)
