# Testing the Copy/Paste Feature

## How to Test

1. **Start the ROAR GUI application**
   ```bash
   python run_gui.py
   ```

2. **Open the Graph Grid View** (if not already showing)
   - The graph grid should show 4 ROARLookupWindow instances in a 2x2 layout

3. **Configure the first window**:
   - Select some items in the tech browser (check some PDK/model/length/corner combinations)
   - Set custom colors on some corners (right-click on corner items)
   - Change X, Y combo selections
   - Toggle some checkboxes (LogX, LogY, 3D, etc.)
   - Adjust spin box values

4. **Test Copy Mode**:
   - Click the "Copy" button on the first window
   - Observe that the "Copy" buttons on the other three windows change to "Paste"
   - The first window's button should remain as "Copy"

5. **Test Paste**:
   - Click "Paste" on any of the other windows (e.g., window 2)
   - Verify that:
     - All tech browser selections are copied
     - Custom colors are preserved
     - Combo box selections match
     - Checkbox states match
     - Spin box values match
     - The graph updates to show the same data
   - All buttons should return to "Copy"

6. **Test Escape Key Cancellation**:
   - Click "Copy" on window 1 again
   - All other windows show "Paste"
   - Press the Escape key
   - Verify that all buttons return to "Copy"
   - No paste operation occurs

7. **Test Multiple Scenarios**:
   - Copy from different windows
   - Copy with different radio button modes (Device Params vs Design Eqs)
   - Copy with 3D mode enabled
   - Copy with different log scale settings
   - Copy with complex tech browser selections

## Expected Behavior

### When Copy is Clicked:
- Source window button stays "Copy"
- All other windows change to "Paste"
- No visual change to the source window

### When Paste is Clicked:
- Target window takes on all settings from source
- Graph updates automatically
- All buttons return to "Copy"
- Copy mode ends

### When Escape is Pressed:
- All buttons return to "Copy"
- No state changes occur
- Copy mode ends
- Works from any window or the grid

## What Gets Copied

1. **Radio Buttons**: Device Params / Design Equations selection
2. **Combo Boxes**: X, Y, Z axis parameter selections
3. **Spin Boxes**: X, Y, Z numeric values
4. **Checkboxes**: 
   - LogX, LogY, LogZ
   - 3D, Contour
   - Legend, Black BG
5. **Settings Grid**: All 4 settings checkboxes
6. **Tech Browser**: 
   - All checked items (PDK/model/length/corner hierarchy)
   - Custom colors for each corner
7. **Graph State**: Automatically updates after paste

## Known Limitations

- Only one copy operation can be active at a time
- The copy is not persistent - it's cleared when paste or cancel occurs
- Attachment checkboxes (settings grid) are restored but may need re-validation based on axis compatibility

## Troubleshooting

If copy/paste doesn't work:
1. Check that the graph_grid reference is properly set on all windows
2. Verify that all four lookup_windows are in the graph_grid.lookup_windows list
3. Check the console for any error messages
4. Ensure the tech_dict is properly shared across all windows
