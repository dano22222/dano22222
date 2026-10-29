# Final technical verification

Checked against the attached assignment and Part 2 feedback on 29 October 2026.

All compulsory technical features are implemented. All 38 automated tests pass. The 1000 NO3 locations each contain 8784 ERA5 hourly observations for 2024. An independent reread of all point caches reproduces the delivered regional mean exactly, with no missing values. SPC identifies 633 hours and LOF identifies 88 hours at the documented defaults.

## Public deployment

The original address remains https://dano22222-u9jpvjhwntlcuukcush85v.streamlit.app/ . The student confirmed the homepage renders. Browser verification subsequently confirmed the public Reservoir Data date controls, STL figure and parameters, spectrogram figure and parameters, full NO3 regional data, SPC statistics (633), LOF statistics (88), and real MongoDB electricity plots for NO2–DK1 in 2025. The earlier loading-screen issue did not persist during this final verification.

## Git and preservation

The earlier Part 2 merge is 8dbf70b. Part 3 was developed on part3-development and visibly merged into main at 5745961, with runtime validation merged at ec5772a. Final documentation is committed on the development branch and merged separately. No historical files, videos, local environments or secrets were deleted. The preservation audit records the original notebooks, initial code backups and videos.

New untracked files with names ending in " 2" were observed in the original project during the final review. Their origin is unverified; they were left untouched and excluded from this delivery commit. Explicit Streamlit page registration uses the canonical files, so these copies are not navigation pages.

## Remaining student actions

1. Read the report and AI-assisted log to ensure they reflect your understanding and experience.
2. Record the five minute screencast using SCREENCAST.md, showing the running original app and explaining the code.
3. Make the video accessible to the assessor and include its link in the Canvas submission comment (or notebook).
4. Upload reports/IND320_Project(P3).pdf to Canvas. Mention that feedback improvements are included if updating a previous submission.

The development log and AI disclosure identify AI assistance explicitly. The geographic administrative proxy and VASS metadata discrepancy are documented scientific limitations, rather than undisclosed exact catchment claims. Raw weather point caches are retained locally; the reproducible downloader, sampled coordinates, complete regional mean and provenance are included in GitHub.

## Latest student edits and folder cleanup

The student-edited Part 3 notebook is preserved with all 12 code cells executed and no saved error outputs. Its AI usage section is also reflected in AI_USAGE.md. A fresh nbconvert WebPDF export contains 22 pages, replacing the earlier custom 13-page export. Historical root files were moved without content changes into archive/cleanup_2026_10_29/previous_root_deliverables/. Numbered copies remain locally archived and ignored by Git; the move manifest documents all locations. VS Code settings hide local environments and caches. The application source and original URL are unchanged.
