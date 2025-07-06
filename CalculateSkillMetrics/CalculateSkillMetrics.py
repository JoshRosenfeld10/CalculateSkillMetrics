import logging
import os
from typing import Optional
from math import sqrt

import vtk
import qt

import slicer
from slicer.i18n import tr as _
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
)


#
# CalculateSkillMetrics
#


class CalculateSkillMetrics(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Calculate Skill Metrics From Sequence")
        self.parent.categories = ["Sequence Utilities"]
        self.parent.dependencies = []
        self.parent.contributors = ["Josh Rosenfeld (Queen's University)"]
        self.parent.helpText = _("""
This module calculates skill metrics using sequence data and tool bounding boxes.
""")


#
# CalculateSkillMetricsParameterNode
#


@parameterNodeWrapper
class CalculateSkillMetricsParameterNode:
    pass


#
# CalculateSkillMetricsWidget
#


class CalculateSkillMetricsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/CalculateSkillMetrics.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)
        self.ui.sequenceBrowserNode.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = CalculateSkillMetricsLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Hide table on load
        self.ui.table.setVisible(False)

        # Buttons
        self.ui.calculateButton.connect("clicked(bool)", self.onCalculateButton)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode: Optional[CalculateSkillMetricsParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            self._checkCanApply()

    def _checkCanApply(self, caller=None, event=None) -> None:
        if self.ui.sequenceBrowserNode.currentNode():
            self.ui.calculateButton.toolTip = _("Calculate skill metrics")
            self.ui.calculateButton.enabled = True
        else:
            self.ui.calculateButton.toolTip = _("Select sequence browser")
            self.ui.calculateButton.enabled = False

    def onCalculateButton(self) -> None:
        """Run processing when user clicks "Apply" button."""
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            self.logic.calculate(
                self.ui.sequenceBrowserNode.currentNode(),
                self.ui.table
            )


#
# CalculateSkillMetricsLogic
#


class CalculateSkillMetricsLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)
        self.sequenceBrowser = None
        self.boundingBoxSequences = []  # format: [[classname, sequenceNode]]

    def getParameterNode(self):
        return CalculateSkillMetricsParameterNode(super().getParameterNode())

    def computeCenterOfBoundingBox(self, markupsNode):
        """
        Computes the center of the bounding box from the four corners
        """
        points = []
        for i in range(markupsNode.GetNumberOfControlPoints()):
            pos = [0, 0 ,0]
            markupsNode.GetNthControlPointPosition(i, pos)

            # Convert x and y coords to mm
            xMM, yMM = self.convertPixelsToMM(pos[0], pos[1], pos[2])

            points.append([xMM, yMM, pos[2]])

        x, y, z = zip(*points)
        return [sum(x) / len(x), sum(y) / len(y), sum(z) / len(z)]

    def convertPixelsToMM(self, xPixels, yPixels, zMM, principlePoint = [314.273, 251.183], focalLength = 592.667):
        xMM = (xPixels - principlePoint[0]) * zMM / focalLength
        yMM = (yPixels - principlePoint[1]) * zMM / focalLength
        return xMM, yMM

    def isFrameValid(self, markupsNode):
        """
        Frame is invalid if the markup points are at (0,0,0).
        This occurs when the tool is out of frame.
        """
        for i in range(markupsNode.GetNumberOfControlPoints()):
            pos = [0, 0 ,0]
            markupsNode.GetNthControlPointPosition(i, pos)
            if pos != [0, 0, 0]:
                return True
        return False

    def calculateMetricsFromSequence(self, boundingBoxSequence):
        numberOfFrames = boundingBoxSequence.GetNumberOfDataNodes()
        centerPathLength = 0.0
        usageTime = 0.0

        lastCenter = None
        lastTimestamp = None

        for i in range(numberOfFrames):
            indexValue = boundingBoxSequence.GetNthIndexValue(i)  # timestamp
            markupsNode = boundingBoxSequence.GetNthDataNode(i)  # markupsNode at timestamp

            # Skip frame if invalid
            if not self.isFrameValid(markupsNode):
                lastCenter = None
                lastTimestamp = None
                continue

            # Convert index value to float timestamp
            timestamp = float(indexValue)

            # Compute center of bounding box
            center = self.computeCenterOfBoundingBox(markupsNode)

            # Compute metrics if previous frame was valid
            if lastCenter is not None and lastTimestamp is not None:
                timeDiff = timestamp - lastTimestamp
                distance = sqrt(sum((center[j] - lastCenter[j]) ** 2 for j in range(3)))  # Euclidean distance of centers
                centerPathLength += distance
                usageTime += timeDiff

            lastCenter = center
            lastTimestamp = timestamp

        return centerPathLength, usageTime

    def calculate(self, sequenceBrowser, table):

        self.sequenceBrowser = sequenceBrowser
        self.boundingBoxSequences = []

        # Get bounding box sequences from sequence browser
        synchronizedSequenceNodes = vtk.vtkCollection()
        self.sequenceBrowser.GetSynchronizedSequenceNodes(synchronizedSequenceNodes)
        for i in range(synchronizedSequenceNodes.GetNumberOfItems()):
            sequenceNode = synchronizedSequenceNodes.GetItemAsObject(i)
            if "Markups Sequence" in sequenceNode.GetName():
                self.boundingBoxSequences.append(
                    [sequenceNode.GetName().split(" ")[0].upper(), sequenceNode]
                )

        # Calculate metrics for each class
        metrics = []
        for i in range(len(self.boundingBoxSequences)):
            currentMetrics = {}
            pathLength, usageTime = self.calculateMetricsFromSequence(self.boundingBoxSequences[i][1])
            currentMetrics["CENTER_PATH_LENGTH"] = pathLength
            currentMetrics["USAGE_TIME"] = usageTime
            currentMetrics["CLASS_NAME"] = self.boundingBoxSequences[i][0]
            metrics.append(currentMetrics)

        # Clear table
        table.clear()

        # Insert columns
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Center Path Length (mm)", "Usage Time (s)"])

        # Set row headers
        table.setRowCount(len(metrics))
        table.setVerticalHeaderLabels([metricData["CLASS_NAME"] for metricData in metrics])

        # Fill row data
        for i in range(len(metrics)):
            table.setItem(i, 0, qt.QTableWidgetItem(str(round(metrics[i]["CENTER_PATH_LENGTH"], 2))))
            table.setItem(i, 1, qt.QTableWidgetItem(str(round(metrics[i]["USAGE_TIME"], 2))))

        # Set table visible
        table.setVisible(True)


#
# CalculateSkillMetricsTest
#


class CalculateSkillMetricsTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
