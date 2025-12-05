import asyncio
import io
import os
import aiohttp
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
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


async def fetch_graph_data(start: str, end: str, rooms: list[str]) -> dict:
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


def load_custom_font(font_file: str):
    """
    Загружает локальный шрифт из файла в проекте.
    :param font_file: Путь к TTF-файлу относительно корня проекта.
    :return: Путь к шрифту.
    """
    # Получаем абсолютный путь к файлу
    font_path = os.path.abspath(font_file)

    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font not found: {font_path}")

    # Добавляем шрифт в matplotlib
    font_manager.fontManager.addfont(font_path)
    return font_path


def setup_plot_style() -> None:
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
        "font.family": "Open Sans",  # Font family
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


def plot_datasets(lang: str | None, ax: Axes, graph_data: dict):
    """
    Processes and plots each dataset from the graph_data.
    :param lang: Language code
    :param ax: Matplotlib axes object
    :param graph_data: Dictionary containing datasets
    :return: DataFrame of the last processed dataset (for limits calculation)
    """
    all_dataframes = []  # Собираем ВСЕ данные сюда

    for ds in graph_data.get("datasets", []):
        if not ds.get("data"):  # Пропускаем пустые датасеты
            continue

        df_part = pd.DataFrame(ds["data"])

        # Защита от кривых данных
        if "x" not in df_part.columns or "y" not in df_part.columns:
            continue

        df_part["x"] = pd.to_datetime(df_part["x"], errors="coerce")
        df_part = df_part.dropna(subset=["x"])  # Убираем невалидные даты
        if df_part.empty:
            continue

        df_part = df_part.sort_values("x")

        # Подпись комнаты
        label_var = ds.get("label", "")
        if label_var and label_var.lower() not in ["суммарные потери"]:
            label_var = get_string(lang, "internet.room", room=label_var)

        border = hex_to_rgba(ds["borderColor"])
        background = hex_to_rgba(ds["backgroundColor"])

        ax.plot(
            df_part["x"], df_part["y"],
            label=label_var,
            color=border,
            linewidth=2,
            solid_capstyle="round"
        )

        if ds.get("fill", False):
            ax.fill_between(
                df_part["x"], df_part["y"], 0,
                color=background,
                interpolate=True,
                zorder=2
            )

        all_dataframes.append(df_part)

    # Если ничего не нарисовано — возвращаем пустой DF (чтобы не упасть ниже)
    if not all_dataframes:
        return pd.DataFrame(columns=["x", "y"])

    # Объединяем все точки и берём общий диапазон
    combined = pd.concat(all_dataframes, ignore_index=True)
    return combined


def _set_fallback_xlim(ax: Axes):
    """Внутренняя функция для запасного диапазона"""
    from datetime import datetime, timedelta
    now = datetime.now()
    start = now - timedelta(hours=config.config.monitoring.back_hours)
    ax.set_xlim(mdates.date2num(start), mdates.date2num(now))


def configure_axes_limits_and_grid(ax: Axes, df: DataFrame):
    """
    Sets y-limits, x-limits, and configures grid and locators.
    :param ax: Matplotlib axes object
    :param df: DataFrame with data for limits
    :return: None
    """
    ax.set_ylim(bottom=-0.1, top=100.1)

    if df.empty or "x" not in df.columns:
        _set_fallback_xlim(ax)
        return

    # Принудительно конвертируем и чистим
    x_dates = pd.to_datetime(df["x"], errors="coerce", utc=True)
    if x_dates.isna().all():
        _set_fallback_xlim(ax)
        return

    # Убираем NaT и берём min/max
    valid_dates = x_dates.dropna()
    if valid_dates.empty:
        _set_fallback_xlim(ax)
    else:
        ax.set_xlim(valid_dates.min(), valid_dates.max())

    ax.yaxis.set_major_locator(MultipleLocator(10))
    ax.yaxis.set_minor_locator(MultipleLocator(5))
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


def add_labels_and_legend(lang: str | None, ax: Axes):
    """
    Adds y-label and configures the legend.
    :param lang: Language code
    :param ax: Matplotlib axes object
    :return: None
    """
    # Set y-axis label
    ax.set_ylabel(get_string(lang, 'internet.losses_y'), fontsize=12)

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


def render_graph_sync(lang: str | None, graph_data: dict, time_len: int, interval: int) -> bytes:
    """
    Main function to render the graph synchronously and return PNG bytes.
    :param lang: Language code
    :param graph_data: Dictionary of graph datasets.
    :param time_len: Length of time in hours.
    :param interval: Interval for ticks in minutes.
    :return: PNG image bytes of the rendered graph.
    """
    load_custom_font("src/res/fonts/OpenSans-Regular.ttf")

    # Step 1: Set up plot style
    setup_plot_style()

    # Step 2: Create figure and axes
    fig, ax = create_figure_and_axes()

    # Step 3: Plot all datasets and get df for limits
    df = plot_datasets(lang, ax, graph_data)

    # Step 4: Configure axes limits and grid
    configure_axes_limits_and_grid(ax, df)

    # Step 5: Configure x-axis ticks and formatter
    configure_xaxis_ticks(ax, df, time_len, interval)

    # Step 6: Auto-format x-date labels with rotation
    fig.autofmt_xdate(rotation=30, ha='right')

    # Step 7: Customize spines
    customize_spines(ax)

    # Step 8: Add labels and legend
    add_labels_and_legend(lang, ax)

    # Step 9: Apply tight layout with padding
    plt.tight_layout(pad=2.5)

    # Step 10: Save to bytes and return
    return save_to_bytes(fig, "#0e1117")


async def render_graph(
        lang: str | None, graph_data: dict, time_len: int, interval: int
) -> bytes:
    """
    :param lang: Language code
    :param graph_data: Dictionary of graph datasets.
    :param time_len: Length of time in hours.
    :param interval: Interval for ticks in minutes.
    :return: PNG image bytes of the rendered graph.
    """
    return await asyncio.to_thread(
        render_graph_sync, lang, graph_data, time_len, interval
    )
