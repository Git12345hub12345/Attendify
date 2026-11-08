"""
Modern Theme and Styling System for Attendify
Provides a cohesive, professional design system with custom widgets
"""

import tkinter as tk
from tkinter import font as tkfont


class ModernTheme:
    """Modern color scheme and styling constants"""
    
    # Primary Colors - Modern blue palette
    PRIMARY = "#1a73e8"        # Modern blue
    PRIMARY_DARK = "#1557b0"   # Darker blue for hover
    PRIMARY_LIGHT = "#4285f4"  # Lighter blue for accents
    
    # Secondary Colors - Green for success/positive actions
    SECONDARY = "#34a853"      # Green for success
    SECONDARY_DARK = "#2d8e47" # Darker green for hover
    
    # Accent Colors - Red for warnings/errors
    ACCENT = "#ea4335"         # Red for warnings/errors
    ACCENT_LIGHT = "#f28b82"   # Light red
    WARNING = "#fbbc04"        # Yellow/orange for warnings
    
    # Neutral Colors - Modern gray palette
    BACKGROUND = "#f8f9fa"     # Light gray background
    SURFACE = "#ffffff"        # White surface
    SURFACE_DARK = "#e8eaed"   # Darker surface
    TEXT_PRIMARY = "#202124"   # Dark gray text
    TEXT_SECONDARY = "#5f6368" # Medium gray text
    BORDER = "#dadce0"         # Light border
    
    # Status Colors
    SUCCESS = "#34a853"
    ERROR = "#ea4335"
    INFO = "#1a73e8"
    
    # Fonts - Modern sans-serif with fallbacks
    FONT_FAMILY = "Segoe UI"   # Modern sans-serif (Windows)
    FONT_FAMILY_FALLBACK = ["Arial", "Helvetica", "sans-serif"]
    
    FONT_TITLE = (FONT_FAMILY, 24, "bold")
    FONT_HEADING = (FONT_FAMILY, 16, "bold")
    FONT_SUBHEADING = (FONT_FAMILY, 14, "bold")
    FONT_BODY = (FONT_FAMILY, 11)
    FONT_BUTTON = (FONT_FAMILY, 11, "bold")
    FONT_SMALL = (FONT_FAMILY, 9)
    
    # Spacing
    PADDING_SMALL = 5
    PADDING_MEDIUM = 10
    PADDING_LARGE = 20
    BORDER_RADIUS = 8
    
    # Shadows (simulated with borders)
    SHADOW_COLOR = "#00000020"
    
    @classmethod
    def get_available_font(cls):
        """Check if preferred font is available, return fallback if not"""
        try:
            available_fonts = tkfont.families()
            if cls.FONT_FAMILY in available_fonts:
                return cls.FONT_FAMILY
            # Try fallbacks
            for fallback in cls.FONT_FAMILY_FALLBACK:
                if fallback in available_fonts:
                    return fallback
            return "TkDefaultFont"
        except:
            return "TkDefaultFont"


class StyledButton(tk.Button):
    """Modern styled button with hover effects and multiple style variants"""
    
    def __init__(self, parent, style="primary", **kwargs):
        # Determine colors based on style type
        if style == "primary":
            bg = ModernTheme.PRIMARY
            hover_bg = ModernTheme.PRIMARY_DARK
            fg = "white"
            active_bg = ModernTheme.PRIMARY_DARK
        elif style == "secondary":
            bg = ModernTheme.SECONDARY
            hover_bg = ModernTheme.SECONDARY_DARK
            fg = "white"
            active_bg = ModernTheme.SECONDARY_DARK
        elif style == "danger":
            bg = ModernTheme.ACCENT
            hover_bg = "#d33b2c"
            fg = "white"
            active_bg = "#d33b2c"
        elif style == "neutral":
            bg = ModernTheme.SURFACE_DARK
            hover_bg = ModernTheme.BORDER
            fg = ModernTheme.TEXT_PRIMARY
            active_bg = ModernTheme.BORDER
        else:
            # Default to primary
            bg = ModernTheme.PRIMARY
            hover_bg = ModernTheme.PRIMARY_DARK
            fg = "white"
            active_bg = ModernTheme.PRIMARY_DARK
        
        # Apply default styling
        default_config = {
            'bg': bg,
            'fg': fg,
            'font': ModernTheme.FONT_BUTTON,
            'relief': 'flat',
            'borderwidth': 0,
            'padx': ModernTheme.PADDING_LARGE,
            'pady': ModernTheme.PADDING_MEDIUM,
            'cursor': 'hand2',
            'activebackground': active_bg,
            'activeforeground': fg
        }
        
        # Merge with user-provided kwargs
        default_config.update(kwargs)
        
        super().__init__(parent, **default_config)
        
        # Store colors for hover effect
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.normal_fg = fg
        
        # Bind hover events
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
    
    def _on_enter(self, event):
        """Handle mouse enter event"""
        if self['state'] != 'disabled':
            self.configure(bg=self.hover_bg)
    
    def _on_leave(self, event):
        """Handle mouse leave event"""
        if self['state'] != 'disabled':
            self.configure(bg=self.normal_bg)


class StyledFrame(tk.Frame):
    """Modern styled frame with optional shadow/elevation effect"""
    
    def __init__(self, parent, elevated=False, **kwargs):
        default_config = {
            'bg': ModernTheme.SURFACE,
            'relief': 'flat',
            'borderwidth': 0
        }
        
        if elevated:
            # Simulate shadow/elevation with border
            default_config['relief'] = 'solid'
            default_config['borderwidth'] = 1
            default_config['highlightbackground'] = ModernTheme.BORDER
            default_config['highlightthickness'] = 1
        
        default_config.update(kwargs)
        super().__init__(parent, **default_config)


class StyleUtils:
    """Utility functions for applying consistent styling"""
    
    @staticmethod
    def create_card(parent, title=None, **kwargs):
        """Create a card-style container with optional title"""
        card = StyledFrame(parent, elevated=True, **kwargs)
        
        if title:
            title_label = tk.Label(
                card,
                text=title,
                font=ModernTheme.FONT_HEADING,
                bg=ModernTheme.SURFACE,
                fg=ModernTheme.TEXT_PRIMARY
            )
            title_label.pack(
                pady=(ModernTheme.PADDING_MEDIUM, ModernTheme.PADDING_SMALL),
                padx=ModernTheme.PADDING_MEDIUM,
                anchor='w'
            )
        
        return card
    
    @staticmethod
    def create_section_header(parent, text):
        """Create a styled section header"""
        return tk.Label(
            parent,
            text=text,
            font=ModernTheme.FONT_HEADING,
            bg=parent['bg'],
            fg=ModernTheme.TEXT_PRIMARY,
            anchor='w'
        )
    
    @staticmethod
    def create_status_badge(parent, text, status_type="info"):
        """Create a colored status badge"""
        colors = {
            "success": ModernTheme.SUCCESS,
            "error": ModernTheme.ERROR,
            "warning": ModernTheme.WARNING,
            "info": ModernTheme.INFO
        }
        
        bg_color = colors.get(status_type, ModernTheme.INFO)
        
        badge = tk.Label(
            parent,
            text=text,
            font=ModernTheme.FONT_SMALL,
            bg=bg_color,
            fg="white",
            padx=ModernTheme.PADDING_SMALL,
            pady=2
        )
        
        return badge
    
    @staticmethod
    def style_entry(entry_widget):
        """Apply modern styling to entry widget"""
        entry_widget.configure(
            font=ModernTheme.FONT_BODY,
            relief='solid',
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=ModernTheme.BORDER,
            highlightcolor=ModernTheme.PRIMARY
        )
