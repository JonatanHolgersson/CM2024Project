import pandas as pd
import numpy as np

# 1. Load the extrapolated file (original data in columns 2, 3, 4)
df_ext = pd.read_csv('1drops50cm_extrapolated.csv', header=None)
time = df_ext[1].values

df_orig = pd.DataFrame({
    0: df_ext[0],
    1: df_ext[1],
    2: df_ext[2],
    3: df_ext[3],
    4: df_ext[4],
    5: df_ext[5]
})

extrapolated_cols = []

# Lower threshold to 15.2 to catch near-cap plateaus
threshold = 15.2

# 2. Loop through columns 3, 4, and 5 (indices 2, 3, 4)
for col_idx in [2, 3, 4]:
    vals = df_orig[col_idx].values.copy()
    clipped = np.abs(vals) >= threshold
    
    if clipped.any():
        clip_indices = np.where(clipped)[0]
        groups = np.split(clip_indices, np.where(np.diff(clip_indices) > 1)[0] + 1)
        
        vals_extrap = vals.copy()
        for group in groups:
            if len(group) == 0:
                continue
            start_idx = group[0]
            end_idx = group[-1]
            
            # Boundary points of the gray zone
            t_start = time[start_idx]
            t_end = time[end_idx]
            v_start = vals[start_idx]
            v_end = vals[end_idx]
            
            # Calculate exact incoming and outgoing slopes from shoulders
            dt_in = time[start_idx] - time[start_idx - 1]
            dv_in = v_start - vals[start_idx - 1]
            slope_start = (dv_in / dt_in) if dt_in > 0 else 0
            
            dt_out = time[end_idx + 1] - time[end_idx]
            dv_out = vals[end_idx + 1] - v_end
            slope_end = (dv_out / dt_out) if dt_out > 0 else 0
            
            dur = t_end - t_start
            if dur <= 0:
                continue
                
            m0 = slope_start * dur
            m1 = slope_end * dur
            
            t_seg = time[start_idx:end_idx+1]
            tau = (t_seg - t_start) / dur
            
            # Cubic Hermite basis functions
            H00 = 2*tau**3 - 3*tau**2 + 1
            H10 = tau**3 - 2*tau**2 + tau
            H01 = -2*tau**3 + 3*tau**2
            H11 = tau**3 - tau**2
            
            segment_vals = v_start * H00 + m0 * H10 + v_end * H01 + m1 * H11
            vals_extrap[start_idx:end_idx+1] = segment_vals
            
        vals = vals_extrap
    extrapolated_cols.append(vals)

# 3. Append the new extrapolated columns (cols 7, 8, 9)
df_orig[6] = extrapolated_cols[0]
df_orig[7] = extrapolated_cols[1]
df_orig[8] = extrapolated_cols[2]

# 4. Recalculate total magnitude (Column 10)
df_orig[9] = np.sqrt(df_orig[6]**2 + df_orig[7]**2 + df_orig[8]**2)

# 5. Save output
output_filename = '1drops50cm_extrapolated.csv'
df_orig.to_csv(output_filename, index=False, header=False)
print(f"Successfully generated {output_filename} with threshold {threshold}!")
