# blender-dottier-anim-retarget
The purpose of this add-on is to retarget and correct animations from one armature to another. It provides multiple ways to adjust the animations to adapt them to the new armature. There are other similar add-ons with the same purpose like [Blender Animation Retargeting](https://github.com/Mwni/blender-animation-retargeting) or 
[Blender Quick Map](https://github.com/Arisego/BlenderQuickMap). They didn't have some of the features that I personally needed, so I decided to make an add-on with some of the things I wanted as a way to practice coding, so if this doesn't work for you maybe check those out.

## How to use

Go into the Sidebar (N) of the 3D Viewport and select "Dottier's Anim Retarget".

**Select the Source and Target armatures. Source is the armature we want to copy the animations from while Target is the armature we want to transfer them to.** 

The Source armature should have the animation we want to transfer active. Any existing keyframes on the Target armature will be replaced once we update them with our configuration, only Euler rotations are excluded because the add-on keyframes the rotation in quaternion. **I recommend removing any keyframes on the Target armature to avoid possible problems. We can change both the Source and Target armatures later even after changing the bones properties on the panel as the properties aren't directly associated with the armatures but with the current scene.** The configuration is saved in the blend file.

![Capturealt](https://github.com/user-attachments/assets/4a18836e-b12a-4dfd-a159-4ad6dbd9a78a)

Once we have both armatures, **click _"Generate Bone Link list"_ to populate the list with the Source Bones and Target Bones, the Source Bones will be automatically assigned to the Target Bones with the same name.** 

If a list already exists, _"Generate Bone Link list"_ will not rewrite the properties of the Target Bones already on the list and will create new rows for the ones that are missing. Every Target Bone entry should be unique, but the same Source Bone can be associated with different Target Bones. **The rows aren't actually associated with the bones, so changing a row with another bone wouldn't transfer his previous configuration.** Any extra rows on the list can be left empty.

![Capture2alt](https://github.com/user-attachments/assets/0a1d0847-257e-421b-8712-678cf28145e8)

After generating the list, we have to **link the Target Bones to the desired Source Bones in the case the bones don't share the same name, are missing, or just aren't the right ones.** To ease the process of linking each bone, we can select both armature while on _"Object Mode"_ and then go into _"Pose Mode"_ to see the bones names. It doesn't matter if we have the Source armature selected while making changes on the panel as only the bones from Target are taken into account.

![Capture4alt](https://github.com/user-attachments/assets/ee35cb35-9838-44b7-9431-7596f6d27d6f)

The list also has filters to ease the linking process. Selecting a Target Bone from the 3D Viewport will automatically add his name to the search filter. The **"_warning symbol button_"** will only show rows that have an invalid bone.

![Capture6](https://github.com/user-attachments/assets/37213171-fc1c-42e6-a993-91e785bcd028)

Once we have the desired Target Bones correctly linked, we can start making adjustments for the animation. **We modify the properties by selecting the specific Target Bone we want to work with from the 3D Viewport while on _"Pose Mode"_. We can select multiple Target Bones and modify their properties collectively. All the properties and operators of the panel only affect the currently selected Target Bones, except the ones related to the list, files and keyframes.**

![Capture7](https://github.com/user-attachments/assets/aa12fd9d-30ff-4395-a894-2e4e086bc344)

**_"Apply view as Offset"_**. Allows you to make transform changes outside of the panel on the 3D Viewport and apply those changes as an Offset. The side button clears those unapplied transform changes.

The _Offset_ properties apply an offset to the Target Bones. _Location Offset_ will be always relative to the Target Bone while _Rotation Offset_ will be relative to the rotation copy.

> Changing a rotation related property or using _"Apply view as Offset"_ will correct the rotation for all the children of the selected Target Bones which are copying the exact rotation of their Source Bone. This doesn't apply to rotation changes made on the 3D Viewport.

**_"Copy Rotation"_**. Copies the exact global rotation of the Source Bone.

**_"Copy Location"_**. Copies the exact global location change of the Source Bone, this is the change relative to the Source Bone's origin which then gets applied to the current Target Bone's location.

**_"Move to Exact"_**. Moves the Target Bone to the exact location of the Source Bone relative to the armature's current location, this means that the location will only be exact when both armature objects are at the same location.

**_"Influence"_**. How much of the location change to apply. The side button sets a rough estimate of the influence obtained by comparing two lengths obtained from the Source Bone and Target bone up to a parent shared by both on their respective armatures.

**_"Set current location as Base"_**. Uses the current location of the Source Bone as his new "origin" from which to apply the location change from. Useful in cases where the _Rest Pose_ of the Source armature doesn't represent an actual "natural pose" of the armature.

**_"Save Config"_** and **_"Load Config"_** allows you to save the current configuration on a .txt file that could be loaded later. If a Target Bone entry is left empty in the list, the row will be ignored.

**_"Clear Bone Link list"_**. Removes all the elements from the Bone Link list. This is the only way of removing elements from the list.

**_"Update All Keyframes"_**. Applies our configuration as keyframes on all frames. If the Target armature already has an animation which has more frames than the animation we are transferring, those extra frames will stay the same.
