import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(value: str | None, default: str) -> str:
    path = Path(value) if value is not None else PROJECT_ROOT / default
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path)


API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_PATH = _resolve_path(os.getenv("SESSION_PATH"), "sessions/collector")
DB_PATH = _resolve_path(os.getenv("DB_PATH"), "data/jobs.db")

# channel_id: naam. Naam yahin se aata hai, Telegram se nahi puchte.
SOURCE_CHANNELS = {
    -1001242584289: "Freshershunt",
    -1002286907886: "Python Experience Jobs",
    -1002688042669: "Freshers IT Jobs",
    -1001243094742: "KickCharm Job Updates",
    -1001521790999: "InternFreak",
    -1001515619731: "Krishan Kumar Jobs Internships",
    -1001309472884: "FresherOffCampus Official",
    -1001475939687: "Jobs and Internships Updates",
    -1001184271074: "Job4Freshers",
    -1001502415672: "Seekeras",
    -1001831837433: "Placementdrive",
    -1001508892192: "Walk-In Drive Jobs",
    -1001299325388: "Off Campus Jobs",
    -1001213962888: "Relocate.Me Jobs",
    -1001409153549: "Jobs Internships Placement Interviews",
    -1001247700218: "OffCampus OnCampus Daily Jobs",
    -1002845471742: "MentorSetu Jobs Internships",
    -1001691188199: "Intern Seeker",
    -1001558771903: "Job4Software",
    -1001515670408: "DevITJobs Netherlands",
    -1001385274097: "Remote Jobs",
    -1001416497399: "DotAware Off-Campus Tech Jobs",
    -1001481121147: "DevITJobs UK",
    -1001231680992: "Work in Startups Remote",
    -1001340606663: "Off Campus Jobs India",
    -1001327742398: "AI Jobs",
    -1001603220106: "Fresher Offcampus Job Drives",
    -1001562730876: "Placementkit",
    -1001299734537: "Go Careers",
    -1001449857072: "FresherDrives",
    -1001188956665: "Way2Freshers",
    -1001827108721: "Placement Lelo",
    -1001348736730: "Singapore Internship Opportunities",
    -1002083547614: "Software Developer Jobs IT Internships",
    -1002137226089: "Remote Jobs Today",
    -1001222491936: "Jobs in Delhi NCR",
    -1001443389827: "OffCampus Phodenge",
    -1001590952025: "OFLATEST Job Updates",
    -1001769262174: "HelloWork Remote IT Jobs",
    -1001765747857: "FresherCareers",
    -1001953744495: "ProSearchBots",
    -1001981841674: "IT Job Alert",
    -1001079882741: "Jobs Abroad",
    -1001766824384: "Remote Software Developer Jobs",
    -1002163064553: "Government Jobs and Internships",
    -1001173511183: "All India Freshers IT Jobs",
    -1001353822828: "Python Jobs",
    -1001220797488: "CRACK IT Off-Campus Drives",
}

if not SOURCE_CHANNELS:
    raise SystemExit("config.py mein SOURCE_CHANNELS khaali hai")


BACKFILL_LIMIT = 20                 # ek channel se max posts
BACKFILL_DELAY = (2.0, 4.0)          # channels ke beech random delay (seconds)
BACKFILL_MAX_FLOOD_WAIT = 300        # isse lamba FloodWait aaye to backfill band





DESTINATION_CHANNELS = {
    "everything": "@OffcampusJobTemple",
    "python_jobs": "@pythonjobsopportunities",
    "it_jobs": "@itjobscse",
}
