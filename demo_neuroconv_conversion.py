from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv() 

# Replace TQDM in NeuroConv
from tqdme import tqdme
import tqdm
tqdm.tqdm = tqdme

# Import NeuroConv
from neuroconv import NWBConverter
from neuroconv.datainterfaces import SpikeGLXRecordingInterface, PhySortingInterface

DEMO_OUTPUT = Path(__file__).parent / "__demo_output__"
DEMO_OUTPUT.mkdir(exist_ok=True)

GUIDE_DEMO_DATA_ROOT = Path.home() / "NWB_GUIDE" / "test-data" / "multi_session_dataset"
if not GUIDE_DEMO_DATA_ROOT.exists():
    raise FileNotFoundError("Please generate the NWB GUIDE test data first")

SUBJECTS = [ "mouse1", "mouse2" ]
SESSIONS = [ "Session1", "Session2" ]

SESSION_SOURCE_DATA = []
for subject in SUBJECTS:
    for session in SESSIONS:
        SESSION_SOURCE_DATA.append(
            dict(
                spikeglx=dict(
                    file_path= str(GUIDE_DEMO_DATA_ROOT / f"{subject}/{subject}_{session}/{subject}_{session}_g0/{subject}_{session}_g0_imec0/{subject}_{session}_g0_t0.imec0.ap.bin"),
                ),
                phy=dict(
                    folder_path= str(GUIDE_DEMO_DATA_ROOT / f"{subject}/{subject}_{session}/{subject}_{session}_phy")
                )
            )
        )

class MyConverter(NWBConverter):
    data_interface_classes = {
        "spikeglx": SpikeGLXRecordingInterface,
        "phy": PhySortingInterface
    }

def get_conversion_options(converter):

    available_options = converter.get_conversion_options_schema()
    options = { interface: {} for interface in MyConverter.data_interface_classes.keys() }

    for interface in options:
        available_opts = available_options.get("properties").get(interface).get("properties", {})

        # Specify if iterator options are available
        if available_opts.get("iterator_opts"):
            options[interface]["iterator_opts"] = dict(
                display_progress=True,
                # progress_bar_class=tqdme
            )

    return options
# ----------------------------------------------------------------------------------------
# ------------------------------------ Run Conversion ------------------------------------
# ----------------------------------------------------------------------------------------

for source_data in SESSION_SOURCE_DATA:
    converter = MyConverter(source_data)
    converter.run_conversion(
        nwbfile_path = DEMO_OUTPUT / f"{subject}_{session}.nwb",
        overwrite = True,
        # metadata=resolved_metadata,
        conversion_options=get_conversion_options(converter)
    )
        