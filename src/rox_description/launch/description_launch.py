# Neobotix GmbH
# Author: Pradheep Padmanabhan
# Contributor: Adarsh Karan K P
# Contributor: Ashin A

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PythonExpression
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue
from launch.conditions import IfCondition
from launch.launch_context import LaunchContext
import xacro
from ament_index_python.packages import get_package_share_directory

def execution_stage(context: LaunchContext,
                    use_sim_time,
                    use_joint_state_publisher_gui,
                    rox_type,
                    imu_enable,
                    d435_enable,
                    arm_type,
                    ur_dc,
                    use_rviz):

    launch_actions = []

    # Launch argument values
    arm_typ = arm_type.perform(context)
    rox_typ = rox_type.perform(context)
    d435 = str(d435_enable.perform(context))
    imu = str(imu_enable.perform(context))
    use_ur_dc = ur_dc.perform(context)
    use_rviz = use_rviz.perform(context)
    use_joint_state_publisher_gui = use_joint_state_publisher_gui.perform(context)
    joint_type = "fixed"
    if rox_typ in ["diff", "trike"]:
        joint_type = "revolute"

    # Paths
    urdf = os.path.join(get_package_share_directory('rox_description'), 'urdf', 'rox.urdf.xacro')
    rviz_launch_file_dir = os.path.join(get_package_share_directory('rox_rviz'), 'launch')
    world_file = os.path.join(get_package_share_directory('rox_description'), 'worlds', 'empty.sdf')
    # =============================
    # --- Launch Gazebo world -----
    # =============================
    launch_actions.append(
        ExecuteProcess(
            cmd=['gz', 'sim', world_file, '-v', '4'],
            output='screen'
        )
    )

    # =============================
    # --- Spawn robot in Gazebo ---
    # =============================
    launch_actions.append(
        Node(
            package="ros_gz_sim",
            executable="create",
            arguments=[
                "-name", "rox_robot",
                "-topic", "robot_description",
                "-x", "0", "-y", "0", "-z", "0.0",
            ],
            output="screen",
        )
    )

    # =============================
    # --- Joint state publisher ---
    # =============================
    start_joint_state_publisher_gui_cmd = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        condition=IfCondition(use_joint_state_publisher_gui),
        name='joint_state_publisher_gui',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    start_joint_state_publisher_cmd = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        condition=IfCondition(PythonExpression(['not ', use_joint_state_publisher_gui])),
        name='joint_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    # =============================
    # --- Robot state publisher ---
    # =============================
    start_robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': ParameterValue(
                Command([
                    "xacro", " ", urdf,
                    " ", 'arm_type:=', arm_typ,
                    " ", 'rox_type:=', rox_typ,
                    " ", 'joint_type:=', joint_type,
                    " ", 'use_imu:=', imu,
                    " ", 'd435_enable:=', d435,
                    " ", 'use_ur_dc:=', use_ur_dc,
                ]),
                value_type=str
            )
        }]
    )

    start_rviz_cmd = IncludeLaunchDescription(
        condition=IfCondition(use_rviz),
        launch_description_source=PythonLaunchDescriptionSource(
            [rviz_launch_file_dir, '/rox_rviz_launch.py'])
    )

    launch_actions.append(start_rviz_cmd)
    launch_actions.append(start_robot_state_publisher_cmd)
    if arm_typ:
        launch_actions.append(start_joint_state_publisher_cmd)
        launch_actions.append(start_joint_state_publisher_gui_cmd)

    return launch_actions

def generate_launch_description():
    # Launch arguments
    ld = LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='False',
                              description='Use simulation clock if True (True/False)'),
        DeclareLaunchArgument('use_joint_state_publisher_gui', default_value='True',
                              description='Use joint state publisher gui if True (True/False)'),
        DeclareLaunchArgument('rox_type', default_value='argo', choices=['', 'argo', 'argo-trio', 'diff', 'trike'],
                              description='ROX Drive Type'),
        DeclareLaunchArgument('imu_enable', default_value='False',
                              description='Enable IMU - True/False'),
        DeclareLaunchArgument('d435_enable', default_value='False',
                              description='Enable Realsense - True/False'),
        DeclareLaunchArgument('arm_type', default_value='', choices=['', 'ur5', 'ur10', 'ur5e', 'ur10e', 'ec66', 'cs66'],
                              description='Arm Types'),
        DeclareLaunchArgument('use_ur_dc', default_value='False',
                              description='Set to True if you have UR arm with DC variant'),
        DeclareLaunchArgument('use_rviz', default_value='True',
                              description='Launch RViz for visualization'),
        # Opaque function to handle execution stage
        OpaqueFunction(
            function=execution_stage,
            args=[
                LaunchConfiguration('use_sim_time'),
                LaunchConfiguration('use_joint_state_publisher_gui'),
                LaunchConfiguration('rox_type'),
                LaunchConfiguration('imu_enable'),
                LaunchConfiguration('d435_enable'),
                LaunchConfiguration('arm_type'),
                LaunchConfiguration('use_ur_dc'),
                LaunchConfiguration('use_rviz')
            ])
    ])
    return ld
