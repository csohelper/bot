import asyncio
import io

import aiohttp
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, FixedLocator
from pandas import DataFrame

from python.storage import config
from python.storage.strings import get_string


def hex_to_rgba(hex_color: str):
    """
    :param hex_color: The hex color string to convert.
    :return: Tuple of RGBA values as floats.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 8:
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        a = int(hex_color[6:8], 16) / 255
    else:
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        a = 1.0
    return r, g, b, a


async def fetch_rooms() -> list[str]:
    """
    :return: List of rooms from the API.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(config.config.monitoring.rooms_endpoint) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["rooms"]


async def fetch_graph_data(start: str, end: str, rooms: list[str]):
    """
    :param start: Start time string.
    :param end: End time string.
    :param rooms: List of room names.
    :return: Graph data JSON from the API.
    """
    async with aiohttp.ClientSession() as session:
        params = {
            "start": start,
            "end": end,
            "rooms": ",".join(rooms)
        }

        async with session.get(config.config.monitoring.graph_endpoint, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()


def setup_plot_style():
    """
    Sets up the dark theme and custom RC parameters for the plot.
    :return: None
    """
    plt.style.use("dark_background")
    plt.rcParams.update({
        "axes.facecolor": "#0e1117",  # Dark background color for axes
        "figure.facecolor": "#0e1117",  # Dark background color for the figure
        "axes.edgecolor": "#303030",  # Edge color for axes
        "axes.grid": True,  # Enable grid
        "grid.color": "#303030",  # Grid line color
        "grid.linestyle": "--",  # Dashed grid lines
        "grid.alpha": 0.5,  # Semi-transparent grid
        "text.color": "#e0e0e0",  # Light text color
        "axes.labelcolor": "#e0e0e0",  # Label color
        "xtick.color": "#e0e0e0",  # X-tick color
        "ytick.color": "#e0e0e0",  # Y-tick color
        "font.size": 11,  # Default font size
        "font.family": "Segoe UI",  # Font family
        "legend.frameon": True,  # Legend frame enabled
        "legend.facecolor": "#1a1a1a",  # Legend background
        "legend.edgecolor": "#404040",  # Legend edge color
        "legend.framealpha": 0.9,  # Legend transparency
    })


def create_figure_and_axes():
    """
    Creates a new figure and axes with specified size and DPI.
    :return: Tuple of (fig, ax)
    """
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    return fig, ax


def plot_datasets(ax: Axes, graph_data: dict):
    """
    Processes and plots each dataset from the graph_data.
    :param ax: Matplotlib axes object
    :param graph_data: Dictionary containing datasets
    :return: DataFrame of the last processed dataset (for limits calculation)
    """
    df = pd.DataFrame()  # Initialize empty DataFrame
    for ds in graph_data["datasets"]:
        # Convert dataset data to DataFrame
        df = pd.DataFrame(ds["data"])
        # Convert 'x' column to datetime
        df["x"] = pd.to_datetime(df["x"])
        # Sort by 'x' to ensure proper order
        df = df.sort_values("x")

        # Modify label if not total or summary
        label_var = ds.get("label", "")
        if label_var.lower() not in ["суммарные потери"]:
            label_var = get_string("internet.room", room=label_var)

        # Convert colors to RGBA
        border = hex_to_rgba(ds["borderColor"])
        background = hex_to_rgba(ds["backgroundColor"])

        # Plot the line
        ax.plot(
            df["x"], df["y"],
            label=label_var,  # Use modified label
            color=border,  # Border color
            linewidth=2,  # Line width
            solid_capstyle="round"  # Rounded line caps
        )

        # Fill area under the curve if 'fill' is True
        if ds.get("fill", False):
            ax.fill_between(
                df["x"], df["y"], 0,
                color=background,  # Fill color
                interpolate=True,  # Interpolate between points
                zorder=2  # Layer order
            )

    return df  # Return the last df for min/max calculations


def configure_axes_limits_and_grid(ax: Axes, df: DataFrame):
    """
    Sets y-limits, x-limits, and configures grid and locators.
    :param ax: Matplotlib axes object
    :param df: DataFrame with data for limits
    :return: None
    """
    # Set y-axis limits from -0.1 to 100.1 to cover 0-100 range nicely
    ax.set_ylim(bottom=-0.1, top=100.1)
    # Set x-axis limits to data range
    ax.set_xlim(df["x"].min(), df["x"].max())

    # Major y-ticks every 10 units
    ax.yaxis.set_major_locator(MultipleLocator(10))
    # Minor y-ticks every 5 units
    ax.yaxis.set_minor_locator(MultipleLocator(5))
    # Disable vertical grid lines for cleaner look
    ax.xaxis.grid(False)


def configure_xaxis_ticks(ax: Axes, df: DataFrame, time_len: int, interval: int):
    """
    Configures x-axis formatter and custom tick locations.
    :param ax: Matplotlib axes object
    :param df: DataFrame with data
    :param time_len: Length of time in hours
    :param interval: Interval for ticks in minutes
    :return: None
    """
    # Format x-ticks as day.month hour:minute
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m %H:%M'))

    # Calculate number of ticks based on time length and interval
    num_ticks = (time_len * 60 // interval) + 1
    # Generate evenly spaced dates for ticks
    tick_dates = pd.date_range(start=df["x"].min(), end=df["x"].max(), periods=num_ticks)

    # Convert dates to matplotlib numbers
    tick_nums = mdates.date2num(tick_dates)

    # Set fixed locator for x-ticks
    ax.xaxis.set_major_locator(FixedLocator(tick_nums))


def customize_spines(ax: Axes):
    """
    Customizes the visibility and color of axis spines.
    :param ax: Matplotlib axes object
    :return: None
    """
    # Hide top spine
    ax.spines['top'].set_visible(False)
    # Hide right spine
    ax.spines['right'].set_visible(False)
    # Hide left spine
    ax.spines['left'].set_visible(False)
    # Set bottom spine color
    ax.spines['bottom'].set_color('#404040')


def add_labels_and_legend(ax: Axes):
    """
    Adds y-label and configures the legend.
    :param ax: Matplotlib axes object
    :return: None
    """
    # Set y-axis label
    ax.set_ylabel(get_string('internet.losses_y'), fontsize=12)

    # Add legend with title
    legend = ax.legend(
        # title="Rooms",  # Legend title
        loc="upper right",  # Position
        frameon=True,  # Frame enabled
        fancybox=False,  # No fancy box
        edgecolor="#404040"  # Edge color
    )
    # Make title bold
    legend.get_title().set_fontweight('bold')
    # Set title color to white
    legend.get_title().set_color("#ffffff")


def save_to_bytes(fig: Figure, facecolor: str) -> bytes:
    """
    Saves the figure to an in-memory PNG buffer.
    :param fig: Matplotlib figure object
    :param facecolor: Background color for saving
    :return: Bytes of the PNG image
    """
    # Create in-memory buffer
    buf = io.BytesIO()
    # Save figure to buffer as PNG
    fig.savefig(
        buf,
        format='png',
        dpi=200,  # High resolution
        facecolor=facecolor,  # Set facecolor
        edgecolor='none'  # No edge color
    )
    # Reset buffer position
    buf.seek(0)
    # Get bytes value
    image_bytes = buf.getvalue()
    # Close plot to free resources
    plt.close()
    return image_bytes


def render_graph_sync(graph_data: dict, time_len: int, interval: int) -> bytes:
    """
    Main function to render the graph synchronously and return PNG bytes.
    :param graph_data: Dictionary of graph datasets.
    :param time_len: Length of time in hours.
    :param interval: Interval for ticks in minutes.
    :return: PNG image bytes of the rendered graph.
    """
    # Step 1: Set up plot style
    setup_plot_style()

    # Step 2: Create figure and axes
    fig, ax = create_figure_and_axes()

    # Step 3: Plot all datasets and get df for limits
    df = plot_datasets(ax, graph_data)

    # Step 4: Configure axes limits and grid
    configure_axes_limits_and_grid(ax, df)

    # Step 5: Configure x-axis ticks and formatter
    configure_xaxis_ticks(ax, df, time_len, interval)

    # Step 6: Auto-format x-date labels with rotation
    fig.autofmt_xdate(rotation=30, ha='right')

    # Step 7: Customize spines
    customize_spines(ax)

    # Step 8: Add labels and legend
    add_labels_and_legend(ax)

    # Step 9: Apply tight layout with padding
    plt.tight_layout(pad=2.5)

    # Step 10: Save to bytes and return
    return save_to_bytes(fig, "#0e1117")


async def render_graph(
        graph_data: dict, time_len: int, interval: int
) -> bytes:
    """
    :param graph_data: Dictionary of graph datasets.
    :param time_len: Length of time in hours.
    :param interval: Interval for ticks in minutes.
    :return: PNG image bytes of the rendered graph.
    """
    return await asyncio.to_thread(
        render_graph_sync, graph_data, time_len, interval
    )
