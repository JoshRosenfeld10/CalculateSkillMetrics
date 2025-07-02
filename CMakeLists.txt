cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(CalculateSkillMetrics)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/CalculateSkillMetrics")
set(EXTENSION_CONTRIBUTORS "Josh Rosenfeld (Queen's University)")
set(EXTENSION_DESCRIPTION "Calculates skill metrics using sequence data and tool bounding boxes.")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/CalculateSkillMetrics.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/CalculateSkillMetrics/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(CalculateSkillMetrics)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
