"""Image Preprocessing for OCR"""
import numpy as np
import cv2
from skimage import exposure, filters
from typing import Optional, Tuple


class ImagePreprocessor:
    """Preprocess images for improved OCR accuracy"""
    
    @staticmethod
    def grayscale(image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale"""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
    
    @staticmethod
    def denoise(image: np.ndarray, method: str = "bilateralFilter") -> np.ndarray:
        """
        Apply denoising to image
        
        Args:
            image: Input image
            method: Denoising method ('bilateralFilter', 'morphological', 'gaussian')
            
        Returns:
            Denoised image
        """
        if method == "bilateralFilter":
            return cv2.bilateralFilter(image, 9, 75, 75)
        elif method == "morphological":
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            opening = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
            return cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        elif method == "gaussian":
            return cv2.GaussianBlur(image, (5, 5), 0)
        return image
    
    @staticmethod
    def thresholding(image: np.ndarray, method: str = "otsu") -> np.ndarray:
        """
        Apply thresholding to image
        
        Args:
            image: Input image (grayscale)
            method: Thresholding method ('otsu', 'adaptive', 'binary')
            
        Returns:
            Thresholded image
        """
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        if method == "otsu":
            _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
        elif method == "adaptive":
            return cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
        elif method == "binary":
            _, thresh = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
            return thresh
        return image
    
    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """Deskew image using moments"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Get text contours
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return image
        
        # Get largest contour
        cnt = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(cnt)
        angle = rect[2]
        
        if angle < -45:
            angle = 90 + angle
        
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        return cv2.warpAffine(
            image, rot_matrix, (w, h),
            borderMode=cv2.BORDER_REPLICATE
        )
    
    @staticmethod
    def resize(image: np.ndarray, scale: float = 2.0) -> np.ndarray:
        """Resize image for better OCR"""
        h, w = image.shape[:2]
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    
    @staticmethod
    def enhance_contrast(image: np.ndarray, method: str = "clahe") -> np.ndarray:
        """
        Enhance image contrast
        
        Args:
            image: Input image
            method: Enhancement method ('clahe', 'histogram')
            
        Returns:
            Enhanced image
        """
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        if method == "clahe":
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)
        elif method == "histogram":
            return cv2.equalizeHist(image)
        return image
    
    @staticmethod
    def remove_borders(image: np.ndarray, border_size: int = 10) -> np.ndarray:
        """Remove borders from image"""
        h, w = image.shape[:2]
        return image[border_size:h-border_size, border_size:w-border_size]
    
    @staticmethod
    def preprocess_pipeline(
        image: np.ndarray,
        deskew: bool = True,
        denoise: bool = True,
        contrast_enhance: bool = True,
        threshold: bool = False,
        resize_scale: Optional[float] = None,
    ) -> np.ndarray:
        """
        Full preprocessing pipeline for OCR
        
        Args:
            image: Input image
            deskew: Whether to deskew
            denoise: Whether to denoise
            contrast_enhance: Whether to enhance contrast
            threshold: Whether to apply thresholding
            resize_scale: Scale factor for resizing (default: 2.0)
            
        Returns:
            Preprocessed image
        """
        result = image.copy()
        
        # Convert to grayscale
        result = ImagePreprocessor.grayscale(result)
        
        # Remove borders
        result = ImagePreprocessor.remove_borders(result, border_size=5)
        
        # Deskew if needed
        if deskew:
            result = ImagePreprocessor.deskew(result)
        
        # Denoise if needed
        if denoise:
            result = ImagePreprocessor.denoise(result, method="bilateralFilter")
        
        # Enhance contrast
        if contrast_enhance:
            result = ImagePreprocessor.enhance_contrast(result, method="clahe")
        
        # Apply thresholding
        if threshold:
            result = ImagePreprocessor.thresholding(result, method="otsu")
        
        # Resize if needed
        if resize_scale:
            result = ImagePreprocessor.resize(result, scale=resize_scale)
        
        return result
