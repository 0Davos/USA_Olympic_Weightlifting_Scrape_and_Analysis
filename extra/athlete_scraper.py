# Scraper for "Rankings", as "Results" isn't conclusive enough for my liking.
from playwright.sync_api import sync_playwright
import time
import pandas as pd

# 248 categories
'''
all_active_weight_classes = ["Women's 11 Under Age Group 36kg", "Women's 11 Under Age Group 40kg", "Women's 11 Under Age Group 44kg", "Women's 11 Under Age Group 48kg", "Women's 11 Under Age Group 53kg", "Women's 11 Under Age Group 58kg", "Women's 11 Under Age Group 63kg", "Women's 11 Under Age Group 63+kg", 
                      "Men's 11 Under Age Group 40kg", "Men's 11 Under Age Group 44kg", "Men's 11 Under Age Group 48kg", "Men's 11 Under Age Group 52kg", "Men's 11 Under Age Group 56kg", "Men's 11 Under Age Group 60kg", "Men's 11 Under Age Group 65kg", "Men's 11 Under Age Group 65+kg", 

                      "Women's 13 Under Age Group 36kg", "Women's 13 Under Age Group 40kg", "Women's 13 Under Age Group 44kg", "Women's 13 Under Age Group 48kg", "Women's 13 Under Age Group 53kg", "Women's 13 Under Age Group 58kg", "Women's 13 Under Age Group 63kg", "Women's 13 Under Age Group 63+kg", 
                      "Men's 13 Under Age Group 40kg", "Men's 13 Under Age Group 44kg", "Men's 13 Under Age Group 48kg", "Men's 13 Under Age Group 52kg", "Men's 13 Under Age Group 56kg", "Men's 13 Under Age Group 60kg", "Men's 13 Under Age Group 65kg", "Men's 13 Under Age Group 65+kg", 
                      
                      "Women's 14-15 Age Group 40kg", "Women's 14-15 Age Group 44kg", "Women's 14-15 Age Group 48kg", "Women's 14-15 Age Group 53kg", "Women's 14-15 Age Group 58kg", "Women's 14-15 Age Group 63kg", "Women's 14-15 Age Group 69kg", "Women's 14-15 Age Group 69+kg", 
                      "Men's 14-15 Age Group 48kg", "Men's 14-15 Age Group 52kg", "Men's 14-15 Age Group 56kg", "Men's 14-15 Age Group 60kg", "Men's 14-15 Age Group 65kg", "Men's 14-15 Age Group 71kg", "Men's 14-15 Age Group 79kg", "Men's 14-15 Age Group 79+kg", 
                      
                      "Women's 16-17 Age Group 44kg", "Women's 16-17 Age Group 48kg", "Women's 16-17 Age Group 53kg", "Women's 16-17 Age Group 58kg", "Women's 16-17 Age Group 63kg", "Women's 16-17 Age Group 69kg", "Women's 16-17 Age Group 77kg", "Women's 16-17 Age Group 77+kg", 
                      "Men's 16-17 Age Group 56kg", "Men's 16-17 Age Group 60kg", "Men's 16-17 Age Group 65kg", "Men's 16-17 Age Group 71kg", "Men's 16-17 Age Group 79kg", "Men's 16-17 Age Group 88kg", "Men's 16-17 Age Group 94kg", "Men's 16-17 Age Group 94+kg", 
                      
                      "Junior Women's 48kg", "Junior Women's 53kg", "Junior Women's 58kg", "Junior Women's 63kg", "Junior Women's 69kg", "Junior Women's 77kg", "Junior Women's 86kg", "Junior Women's 86+kg", 
                      "Junior Men's 60kg", "Junior Men's 65kg", "Junior Men's 71kg", "Junior Men's 79kg", "Junior Men's 88kg", "Junior Men's 94kg", "Junior Men's 110kg", "Junior Men's 110+kg", 
                      
                      "Women's Masters (35-39) 48kg", "Women's Masters (35-39) 53kg", "Women's Masters (35-39) 58kg", "Women's Masters (35-39) 63kg", "Women's Masters (35-39) 69kg", "Women's Masters (35-39) 77kg", "Women's Masters (35-39) 86kg", "Women's Masters (35-39) 86+kg", 
                      "Men's Masters (35-39) 60kg", "Men's Masters (35-39) 65kg", "Men's Masters (35-39) 71kg", "Men's Masters (35-39) 79kg", "Men's Masters (35-39) 88kg", "Men's Masters (35-39) 94kg", "Men's Masters (35-39) 110kg", "Men's Masters (35-39) 110+kg", 
                      
                      "Women's Masters (40-44) 48kg", "Women's Masters (40-44) 53kg", "Women's Masters (40-44) 58kg", "Women's Masters (40-44) 63kg", "Women's Masters (40-44) 69kg", "Women's Masters (40-44) 77kg", "Women's Masters (40-44) 86kg", "Women's Masters (40-44) 86+kg", 
                      "Men's Masters (40-44) 60kg", "Men's Masters (40-44) 65kg", "Men's Masters (40-44) 71kg", "Men's Masters (40-44) 79kg", "Men's Masters (40-44) 88kg", "Men's Masters (40-44) 94kg", "Men's Masters (40-44) 110kg", "Men's Masters (40-44) 110+kg", 
                      
                      "Women's Masters (45-49) 48kg", "Women's Masters (45-49) 53kg", "Women's Masters (45-49) 58kg", "Women's Masters (45-49) 63kg", "Women's Masters (45-49) 69kg", "Women's Masters (45-49) 77kg", "Women's Masters (45-49) 86kg", "Women's Masters (45-49) 86+kg", 
                      "Men's Masters (45-49) 60kg", "Men's Masters (45-49) 65kg", "Men's Masters (45-49) 71kg", "Men's Masters (45-49) 79kg", "Men's Masters (45-49) 88kg", "Men's Masters (45-49) 94kg", "Men's Masters (45-49) 110kg", "Men's Masters (45-49) 110+kg", 
                      
                      "Women's Masters (50-54) 48kg", "Women's Masters (50-54) 53kg", "Women's Masters (50-54) 58kg", "Women's Masters (50-54) 63kg", "Women's Masters (50-54) 69kg", "Women's Masters (50-54) 77kg", "Women's Masters (50-54) 86kg", "Women's Masters (50-54) 86+kg", 
                      "Men's Masters (50-54) 60kg", "Men's Masters (50-54) 65kg", "Men's Masters (50-54) 71kg", "Men's Masters (50-54) 79kg", "Men's Masters (50-54) 88kg", "Men's Masters (50-54) 94kg", "Men's Masters (50-54) 110kg", "Men's Masters (50-54) 110+kg", 

                      "Women's Masters (55-59) 48kg", "Women's Masters (55-59) 53kg", "Women's Masters (55-59) 58kg", "Women's Masters (55-59) 63kg", "Women's Masters (55-59) 69kg", "Women's Masters (55-59) 77kg", "Women's Masters (55-59) 86kg", "Women's Masters (55-59) 86+kg", 
                      "Men's Masters (55-59) 60kg", "Men's Masters (55-59) 65kg", "Men's Masters (55-59) 71kg", "Men's Masters (55-59) 79kg", "Men's Masters (55-59) 88kg", "Men's Masters (55-59) 94kg", "Men's Masters (55-59) 110kg", "Men's Masters (55-59) 110+kg", 
                      
                      "Women's Masters (60-64) 48kg", "Women's Masters (60-64) 53kg", "Women's Masters (60-64) 58kg", "Women's Masters (60-64) 63kg", "Women's Masters (60-64) 69kg", "Women's Masters (60-64) 77kg", "Women's Masters (60-64) 86kg", "Women's Masters (60-64) 86+kg", 
                      "Men's Masters (60-64) 60kg", "Men's Masters (60-64) 65kg", "Men's Masters (60-64) 71kg", "Men's Masters (60-64) 79kg", "Men's Masters (60-64) 88kg", "Men's Masters (60-64) 94kg", "Men's Masters (60-64) 110kg", "Men's Masters (60-64) 110+kg", 
                      
                      "Women's Masters (65-69) 48kg", "Women's Masters (65-69) 53kg", "Women's Masters (65-69) 58kg", "Women's Masters (65-69) 63kg", "Women's Masters (65-69) 69kg", "Women's Masters (65-69) 77kg", "Women's Masters (65-69) 86kg", "Women's Masters (65-69) 86+kg", 
                      "Men's Masters (65-69) 60kg", "Men's Masters (65-69) 65kg", "Men's Masters (65-69) 71kg", "Men's Masters (65-69) 79kg", "Men's Masters (65-69) 88kg", "Men's Masters (65-69) 94kg", "Men's Masters (65-69) 110kg", "Men's Masters (65-69) 110+kg", 

                      "Women's Masters (70-74) 48kg", "Women's Masters (70-74) 53kg", "Women's Masters (70-74) 58kg", "Women's Masters (70-74) 63kg", "Women's Masters (70-74) 69kg", "Women's Masters (70-74) 77kg", "Women's Masters (70-74) 86kg", "Women's Masters (70-74) 86+kg", 
                      "Men's Masters (70-74) 60kg", "Men's Masters (70-74) 65kg", "Men's Masters (70-74) 71kg", "Men's Masters (70-74) 79kg", "Men's Masters (70-74) 88kg", "Men's Masters (70-74) 94kg", "Men's Masters (70-74) 110kg", "Men's Masters (70-74) 110+kg", 
                      
                      "Women's Masters (75+) 48kg", "Women's Masters (75+) 53kg", "Women's Masters (75+) 58kg", "Women's Masters (75+) 63kg", "Women's Masters (75+) 69kg", "Women's Masters (75+) 77kg", "Women's Masters (75+) 86kg", "Women's Masters (75+) 86+kg",
                      "Men's Masters (75-79) 60kg", "Men's Masters (75-79) 65kg", "Men's Masters (75-79) 71kg", "Men's Masters (75-79) 79kg", "Men's Masters (75-79) 88kg", "Men's Masters (75-79) 94kg", "Men's Masters (75-79) 110kg", "Men's Masters (75-79) 110+kg", 
                      
                      "Open Women's 48kg", "Open Women's 53kg", "Open Women's 58kg", "Open Women's 63kg", "Open Women's 69kg", "Open Women's 77kg", "Open Women's 86kg", "Open Women's 86+kg", 
                      "Open Men's 60kg", "Open Men's 65kg", "Open Men's 71kg", "Open Men's 79kg", "Open Men's 88kg", "Open Men's 94kg", "Open Men's 110kg", "Open Men's 110+kg", 
                      
                       "Men's Masters (80+) 60kg", "Men's Masters (80+) 65kg", "Men's Masters (80+) 71kg", "Men's Masters (80+) 79kg", "Men's Masters (80+) 88kg", "Men's Masters (80+) 94kg", "Men's Masters (80+) 110kg", "Men's Masters (80+) 110+kg"
                       ]

'''

# All old weight classes


heat1 = ["Women's 11 Under Age Group 36kg", "Women's 11 Under Age Group 40kg", "Women's 11 Under Age Group 44kg", "Women's 11 Under Age Group 48kg", "Women's 11 Under Age Group 53kg", "Women's 11 Under Age Group 58kg", "Women's 11 Under Age Group 63kg", "Women's 11 Under Age Group 63+kg", 
                      "Men's 11 Under Age Group 40kg", "Men's 11 Under Age Group 44kg", "Men's 11 Under Age Group 48kg", "Men's 11 Under Age Group 52kg", "Men's 11 Under Age Group 56kg", "Men's 11 Under Age Group 60kg", "Men's 11 Under Age Group 65kg", "Men's 11 Under Age Group 65+kg", 

                      "Women's 13 Under Age Group 36kg", "Women's 13 Under Age Group 40kg", "Women's 13 Under Age Group 44kg", "Women's 13 Under Age Group 48kg", "Women's 13 Under Age Group 53kg", "Women's 13 Under Age Group 58kg", "Women's 13 Under Age Group 63kg", "Women's 13 Under Age Group 63+kg", 
                      "Men's 13 Under Age Group 40kg", "Men's 13 Under Age Group 44kg", "Men's 13 Under Age Group 48kg", "Men's 13 Under Age Group 52kg", "Men's 13 Under Age Group 56kg", "Men's 13 Under Age Group 60kg", "Men's 13 Under Age Group 65kg", "Men's 13 Under Age Group 65+kg", 
                      ]
heat2 = ["Women's 14-15 Age Group 40kg", "Women's 14-15 Age Group 44kg", "Women's 14-15 Age Group 48kg", "Women's 14-15 Age Group 53kg", "Women's 14-15 Age Group 58kg", "Women's 14-15 Age Group 63kg", "Women's 14-15 Age Group 69kg", "Women's 14-15 Age Group 69+kg", 
                      "Men's 14-15 Age Group 48kg", "Men's 14-15 Age Group 52kg", "Men's 14-15 Age Group 56kg", "Men's 14-15 Age Group 60kg", "Men's 14-15 Age Group 65kg", "Men's 14-15 Age Group 71kg", "Men's 14-15 Age Group 79kg", "Men's 14-15 Age Group 79+kg", 
                      
                      "Women's 16-17 Age Group 44kg", "Women's 16-17 Age Group 48kg", "Women's 16-17 Age Group 53kg", "Women's 16-17 Age Group 58kg", "Women's 16-17 Age Group 63kg", "Women's 16-17 Age Group 69kg", "Women's 16-17 Age Group 77kg", "Women's 16-17 Age Group 77+kg", 
                      "Men's 16-17 Age Group 56kg", "Men's 16-17 Age Group 60kg", "Men's 16-17 Age Group 65kg", "Men's 16-17 Age Group 71kg", "Men's 16-17 Age Group 79kg", "Men's 16-17 Age Group 88kg", "Men's 16-17 Age Group 94kg", "Men's 16-17 Age Group 94+kg", 
                      ]
heat3 = [
                      "Junior Women's 48kg", "Junior Women's 53kg", "Junior Women's 58kg", "Junior Women's 63kg", "Junior Women's 69kg", "Junior Women's 77kg", "Junior Women's 86kg", "Junior Women's 86+kg", 
                      "Junior Men's 60kg", "Junior Men's 65kg", "Junior Men's 71kg", "Junior Men's 79kg", "Junior Men's 88kg", "Junior Men's 94kg", "Junior Men's 110kg", "Junior Men's 110+kg", 
                      
                      "Women's Masters (35-39) 48kg", "Women's Masters (35-39) 53kg", "Women's Masters (35-39) 58kg", "Women's Masters (35-39) 63kg", "Women's Masters (35-39) 69kg", "Women's Masters (35-39) 77kg", "Women's Masters (35-39) 86kg", "Women's Masters (35-39) 86+kg", 
                      "Men's Masters (35-39) 60kg", "Men's Masters (35-39) 65kg", "Men's Masters (35-39) 71kg", "Men's Masters (35-39) 79kg", "Men's Masters (35-39) 88kg", "Men's Masters (35-39) 94kg", "Men's Masters (35-39) 110kg", "Men's Masters (35-39) 110+kg", 
                      ]
heat4 = ["Women's Masters (40-44) 48kg", "Women's Masters (40-44) 53kg", "Women's Masters (40-44) 58kg", "Women's Masters (40-44) 63kg", "Women's Masters (40-44) 69kg", "Women's Masters (40-44) 77kg", "Women's Masters (40-44) 86kg", "Women's Masters (40-44) 86+kg", 
                      "Men's Masters (40-44) 60kg", "Men's Masters (40-44) 65kg", "Men's Masters (40-44) 71kg", "Men's Masters (40-44) 79kg", "Men's Masters (40-44) 88kg", "Men's Masters (40-44) 94kg", "Men's Masters (40-44) 110kg", "Men's Masters (40-44) 110+kg", 
                      
                      "Women's Masters (45-49) 48kg", "Women's Masters (45-49) 53kg", "Women's Masters (45-49) 58kg", "Women's Masters (45-49) 63kg", "Women's Masters (45-49) 69kg", "Women's Masters (45-49) 77kg", "Women's Masters (45-49) 86kg", "Women's Masters (45-49) 86+kg", 
                      "Men's Masters (45-49) 60kg", "Men's Masters (45-49) 65kg", "Men's Masters (45-49) 71kg", "Men's Masters (45-49) 79kg", "Men's Masters (45-49) 88kg", "Men's Masters (45-49) 94kg", "Men's Masters (45-49) 110kg", "Men's Masters (45-49) 110+kg", 
                      ]
heat5 = ["Women's Masters (50-54) 48kg", "Women's Masters (50-54) 53kg", "Women's Masters (50-54) 58kg", "Women's Masters (50-54) 63kg", "Women's Masters (50-54) 69kg", "Women's Masters (50-54) 77kg", "Women's Masters (50-54) 86kg", "Women's Masters (50-54) 86+kg", 
                      "Men's Masters (50-54) 60kg", "Men's Masters (50-54) 65kg", "Men's Masters (50-54) 71kg", "Men's Masters (50-54) 79kg", "Men's Masters (50-54) 88kg", "Men's Masters (50-54) 94kg", "Men's Masters (50-54) 110kg", "Men's Masters (50-54) 110+kg", 

                      "Women's Masters (55-59) 48kg", "Women's Masters (55-59) 53kg", "Women's Masters (55-59) 58kg", "Women's Masters (55-59) 63kg", "Women's Masters (55-59) 69kg", "Women's Masters (55-59) 77kg", "Women's Masters (55-59) 86kg", "Women's Masters (55-59) 86+kg", 
                      "Men's Masters (55-59) 60kg", "Men's Masters (55-59) 65kg", "Men's Masters (55-59) 71kg", "Men's Masters (55-59) 79kg", "Men's Masters (55-59) 88kg", "Men's Masters (55-59) 94kg", "Men's Masters (55-59) 110kg", "Men's Masters (55-59) 110+kg", 
                      ]
heat6 = ["Women's Masters (60-64) 48kg", "Women's Masters (60-64) 53kg", "Women's Masters (60-64) 58kg", "Women's Masters (60-64) 63kg", "Women's Masters (60-64) 69kg", "Women's Masters (60-64) 77kg", "Women's Masters (60-64) 86kg", "Women's Masters (60-64) 86+kg", 
                      "Men's Masters (60-64) 60kg", "Men's Masters (60-64) 65kg", "Men's Masters (60-64) 71kg", "Men's Masters (60-64) 79kg", "Men's Masters (60-64) 88kg", "Men's Masters (60-64) 94kg", "Men's Masters (60-64) 110kg", "Men's Masters (60-64) 110+kg", 
                      
                      "Women's Masters (65-69) 48kg", "Women's Masters (65-69) 53kg", "Women's Masters (65-69) 58kg", "Women's Masters (65-69) 63kg", "Women's Masters (65-69) 69kg", "Women's Masters (65-69) 77kg", "Women's Masters (65-69) 86kg", "Women's Masters (65-69) 86+kg", 
                      "Men's Masters (65-69) 60kg", "Men's Masters (65-69) 65kg", "Men's Masters (65-69) 71kg", "Men's Masters (65-69) 79kg", "Men's Masters (65-69) 88kg", "Men's Masters (65-69) 94kg", "Men's Masters (65-69) 110kg", "Men's Masters (65-69) 110+kg", 
                      ]
heat7 = ["Women's Masters (70-74) 48kg", "Women's Masters (70-74) 53kg", "Women's Masters (70-74) 58kg", "Women's Masters (70-74) 63kg", "Women's Masters (70-74) 69kg", "Women's Masters (70-74) 77kg", "Women's Masters (70-74) 86kg", "Women's Masters (70-74) 86+kg", 
                      "Men's Masters (70-74) 60kg", "Men's Masters (70-74) 65kg", "Men's Masters (70-74) 71kg", "Men's Masters (70-74) 79kg", "Men's Masters (70-74) 88kg", "Men's Masters (70-74) 94kg", "Men's Masters (70-74) 110kg", "Men's Masters (70-74) 110+kg", 
                      
                      "Women's Masters (75+) 48kg", "Women's Masters (75+) 53kg", "Women's Masters (75+) 58kg", "Women's Masters (75+) 63kg", "Women's Masters (75+) 69kg", "Women's Masters (75+) 77kg", "Women's Masters (75+) 86kg", "Women's Masters (75+) 86+kg",
                      "Men's Masters (75-79) 60kg", "Men's Masters (75-79) 65kg", "Men's Masters (75-79) 71kg", "Men's Masters (75-79) 79kg", "Men's Masters (75-79) 88kg", "Men's Masters (75-79) 94kg", "Men's Masters (75-79) 110kg", "Men's Masters (75-79) 110+kg", 
                      ]
heat8 = ["Open Women's 48kg", "Open Women's 53kg", "Open Women's 58kg", "Open Women's 63kg", "Open Women's 69kg", "Open Women's 77kg", "Open Women's 86kg", "Open Women's 86+kg", 
                      "Open Men's 60kg", "Open Men's 65kg", "Open Men's 71kg", "Open Men's 79kg", "Open Men's 88kg", "Open Men's 94kg", "Open Men's 110kg", "Open Men's 110+kg", 
                      
                       "Men's Masters (80+) 60kg", "Men's Masters (80+) 65kg", "Men's Masters (80+) 71kg", "Men's Masters (80+) 79kg", "Men's Masters (80+) 88kg", "Men's Masters (80+) 94kg", "Men's Masters (80+) 110kg", "Men's Masters (80+) 110+kg"
                       ]
all_active_weight_classes = [heat1, heat2, heat3, heat4, heat5, heat6, heat7, heat8]

# 531 categories
all_old_weight_classes = [
    "(Inactive) Junior Women's +75 Kg",
    "(Inactive) Women's Masters (35-39) +75 kg",
    "(Inactive) Women's Masters (40-44) +75 kg",
    "(Inactive) Women's Masters (45-49) +75 kg",
    "(Inactive) Women's Masters (50-54) +75 kg",
    "(Inactive) Women's Masters (55-59) +75 kg",
    "(Inactive) Women's Masters (60-64) +75 kg",
    "(Inactive) Women's Masters (65-69) +75 kg",
    "(Inactive) Women's Masters (70-74) +75 kg",
    "(Inactive) Open Women's +75 Kg",
    "(Inactive) Women's Masters (75+) +75 kg",
    "(Inactive) Women's 13 Under Age Group 31kg",
    "(Inactive) Women's 13 Under Age Group 35kg",
    "(Inactive) Women's 13 Under Age Group 39kg",
    "(Inactive) Women's 13 Under Age Group 44kg",
    "(Inactive) Women's 13 Under Age Group 48kg",
    "(Inactive) Women's 13 Under Age Group 53kg",
    "(Inactive) Women's 13 Under Age Group 58kg",
    "(Inactive) Women's 13 Under Age Group +58 Kg",
    "(Inactive) Men's 13 Under Age Group 31 Kg",
    "(Inactive) Men's 13 Under Age Group 35 Kg",
    "(Inactive) Men's 13 Under Age Group 50 Kg",
    "(Inactive) Men's 13 Under Age Group 56 Kg",
    "(Inactive) Men's 13 Under Age Group 62 Kg",
    "(Inactive) Men's 13 Under Age Group 69 Kg",
    "(Inactive) Men's 13 Under Age Group +69 Kg",
    "(Inactive) Women's 14-15 Age Group 44 kg",
    "(Inactive) Women's 14-15 Age Group 48 kg",
    "(Inactive) Women's 14-15 Age Group 53 kg",
    "(Inactive) Women's 14-15 Age Group 58 kg",
    "(Inactive) Women's 14-15 Age Group 63 kg",
    "(Inactive) Women's 14-15 Age Group 69 kg",
    "(Inactive) Women's 14-15 Age Group +69 kg",
    "(Inactive) Men's 14-15 Age Group 50 Kg",
    "(Inactive) Men's 14-15 Age Group 56 Kg",
    "(Inactive) Men's 14-15 Age Group 62 kg",
    "(Inactive) Men's 14-15 Age Group 69 kg",
    "(Inactive) Men's 14-15 Age Group 77 kg",
    "(Inactive) Men's 14-15 Age Group 85 Kg",
    "(Inactive) Men's 14-15 Age Group +85 kg",
    "(Inactive) Women's 16-17 Age Group 44 kg",
    "(Inactive) Women's 16-17 Age Group 48 kg",
    "(Inactive) Women's 16-17 Age Group 53 kg",
    "(Inactive) Women's 16-17 Age Group 58 kg",
    "(Inactive) Women's 16-17 Age Group 63 kg",
    "(Inactive) Women's 16-17 Age Group 69 kg",
    "(Inactive) Women's 16-17 Age Group 75 kg",
    "(Inactive) Women's 16-17 Age Group +75 kg",
    "(Inactive) Men's 16-17 Age Group 50 kg",
    "(Inactive) Men's 16-17 Age Group 56 kg",
    "(Inactive) Men's 16-17 Age Group 62 kg",
    "(Inactive) Men's 16-17 Age Group 69 kg",
    "(Inactive) Men's 16-17 Age Group 77 kg",
    "(Inactive) Men's 16-17 Age Group 85 kg",
    "(Inactive) Men's 16-17 Age Group 94 kg",
    "(Inactive) Men's 16-17 Age Group 105 kg",
    "(Inactive) Men's 16-17 Age Group +105 kg",
    "(Inactive) Junior Women's 48 kg",
    "(Inactive) Junior Women's 53 kg",
    "(Inactive) Junior Women's 58 kg",
    "(Inactive) Junior Women's 63 kg",
    "(Inactive) Junior Women's 69 kg",
    "(Inactive) Junior Women's 75 kg",
    "(Inactive) Junior Women's 90 kg",
    "(Inactive) Junior Women's +90 kg",
    "(Inactive) Junior Men's 56 kg",
    "(Inactive) Junior Men's 62 kg",
    "(Inactive) Junior Men's 69 kg",
    "(Inactive) Junior Men's 77 kg",
    "(Inactive) Junior Men's 85 kg",
    "(Inactive) Junior Men's 94 kg",
    "(Inactive) Junior Men's 105 kg",
    "(Inactive) Junior Men's +105 kg",
    "(Inactive) Women's Masters (35-39) 48 kg",
    "(Inactive) Women's Masters (35-39) 53 kg",
    "(Inactive) Women's Masters (35-39) 58 kg",
    "(Inactive) Women's Masters (35-39) 63 kg",
    "(Inactive) Women's Masters (35-39) 69 kg",
    "(Inactive) Women's Masters (35-39) 75 kg",
    "(Inactive) Women's Masters (35-39) 90 kg",
    "(Inactive) Women's Masters (35-39) +90 kg",
    "(Inactive) Men's Masters (35-39) 56 kg",
    "(Inactive) Men's Masters (35-39) 62 kg",
    "(Inactive) Men's Masters (35-39) 69 kg",
    "(Inactive) Men's Masters (35-39) 77 kg",
    "(Inactive) Men's Masters (35-39) 85 kg",
    "(Inactive) Men's Masters (35-39) 94 kg",
    "(Inactive) Men's Masters (35-39) 105 kg",
    "(Inactive) Men's Masters (35-39) +105 kg",
    "(Inactive) Women's Masters (40-44) 48 kg",
    "(Inactive) Women's Masters (40-44) 53 kg",
    "(Inactive) Women's Masters (40-44) 58 kg",
    "(Inactive) Women's Masters (40-44) 63 kg",
    "(Inactive) Women's Masters (40-44) 69 kg",
    "(Inactive) Women's Masters (40-44) 75 kg",
    "(Inactive) Women's Masters (40-44) 90 kg",
    "(Inactive) Women's Masters (40-44) +90 kg",
    "(Inactive) Men's Masters (40-44) 56 kg",
    "(Inactive) Men's Masters (40-44) 62 kg",
    "(Inactive) Men's Masters (40-44) 69 kg",
    "(Inactive) Men's Masters (40-44) 77 kg",
    "(Inactive) Men's Masters (40-44) 85 kg",
    "(Inactive) Men's Masters (40-44) 94 kg",
    "(Inactive) Men's Masters (40-44) 105 kg",
    "(Inactive) Men's Masters (40-44) +105 kg",
    "(Inactive) Women's Masters (45-49) 48 kg",
    "(Inactive) Women's Masters (45-49) 53 kg",
    "(Inactive) Women's Masters (45-49) 58 kg",
    "(Inactive) Women's Masters (45-49) 63 kg",
    "(Inactive) Women's Masters (45-49) 69 kg",
    "(Inactive) Women's Masters (45-49) 75 kg",
    "(Inactive) Women's Masters (45-49) 90 kg",
    "(Inactive) Women's Masters (45-49) +90 kg",
    "(Inactive) Men's Masters (45-49) 56 kg",
    "(Inactive) Men's Masters (45-49) 62 kg",
    "(Inactive) Men's Masters (45-49) 69 kg",
    "(Inactive) Men's Masters (45-49) 77 kg",
    "(Inactive) Men's Masters (45-49) 85 kg",
    "(Inactive) Men's Masters (45-49) 94 kg",
    "(Inactive) Men's Masters (45-49) 105 kg",
    "(Inactive) Men's Masters (45-49) +105 kg",
    "(Inactive) Women's Masters (50-54) 48 kg",
    "(Inactive) Women's Masters (50-54) 53 kg",
    "(Inactive) Women's Masters (50-54) 58 kg",
    "(Inactive) Women's Masters (50-54) 63 kg",
    "(Inactive) Women's Masters (50-54) 69 kg",
    "(Inactive) Women's Masters (50-54) 75 kg",
    "(Inactive) Women's Masters (50-54) 90 kg",
    "(Inactive) Women's Masters (50-54) +90 kg",
    "(Inactive) Men's Masters (50-54) 56 kg",
    "(Inactive) Men's Masters (50-54) 62 kg",
    "(Inactive) Men's Masters (50-54) 69 kg",
    "(Inactive) Men's Masters (50-54) 77 kg",
    "(Inactive) Men's Masters (50-54) 85 kg",
    "(Inactive) Men's Masters (50-54) 94 kg",
    "(Inactive) Men's Masters (50-54) 105 kg",
    "(Inactive) Men's Masters (50-54) +105 kg",
    "(Inactive) Women's Masters (55-59) 48 kg",
    "(Inactive) Women's Masters (55-59) 53 kg",
    "(Inactive) Women's Masters (55-59) 58 kg",
    "(Inactive) Women's Masters (55-59) 63 kg",
    "(Inactive) Women's Masters (55-59) 69 kg",
    "(Inactive) Women's Masters (55-59) 75 kg",
    "(Inactive) Women's Masters (55-59) 90 kg",
    "(Inactive) Women's Masters (55-59) +90 kg",
    "(Inactive) Men's Masters (55-59) 56 kg",
    "(Inactive) Men's Masters (55-59) 62 kg",
    "(Inactive) Men's Masters (55-59) 69 kg",
    "(Inactive) Men's Masters (55-59) 77 kg",
    "(Inactive) Men's Masters (55-59) 85 kg",
    "(Inactive) Men's Masters (55-59) 94 kg",
    "(Inactive) Men's Masters (55-59) 105 kg",
    "(Inactive) Men's Masters (55-59) +105 kg",
    "(Inactive) Women's Masters (60-64) 48 kg",
    "(Inactive) Women's Masters (60-64) 53 kg",
    "(Inactive) Women's Masters (60-64) 58 kg",
    "(Inactive) Women's Masters (60-64) 63 kg",
    "(Inactive) Women's Masters (60-64) 69 kg",
    "(Inactive) Women's Masters (60-64) 75 kg",
    "(Inactive) Women's Masters (60-64) 90 kg",
    "(Inactive) Women's Masters (60-64) +90 kg",
    "(Inactive) Men's Masters (60-64) 56 kg",
    "(Inactive) Men's Masters (60-64) 62 kg",
    "(Inactive) Men's Masters (60-64) 69 kg",
    "(Inactive) Men's Masters (60-64) 77 kg",
    "(Inactive) Men's Masters (60-64) 85 kg",
    "(Inactive) Men's Masters (60-64) 94 kg",
    "(Inactive) Men's Masters (60-64) 105 kg",
    "(Inactive) Men's Masters (60-64) +105 kg",
    "(Inactive) Women's Masters (65-69) 48 kg",
    "(Inactive) Women's Masters (65-69) 53 kg",
    "(Inactive) Women's Masters (65-69) 58 kg",
    "(Inactive) Women's Masters (65-69) 63 kg",
    "(Inactive) Women's Masters (65-69) 69 kg",
    "(Inactive) Women's Masters (65-69) 75 kg",
    "(Inactive) Women's Masters (65-69) 90 kg",
    "(Inactive) Women's Masters (65-69) +90 kg",
    "(Inactive) Men's Masters (65-69) 56 kg",
    "(Inactive) Men's Masters (65-69) 62 kg",
    "(Inactive) Men's Masters (65-69) 69 kg",
    "(Inactive) Men's Masters (65-69) 77 kg",
    "(Inactive) Men's Masters (65-69) 85 kg",
    "(Inactive) Men's Masters (65-69) 94 kg",
    "(Inactive) Men's Masters (65-69) 105 kg",
    "(Inactive) Men's Masters (65-69) +105 kg",
    "(Inactive) Women's Masters (70-74) 48 kg",
    "(Inactive) Women's Masters (70-74) 53 kg",
    "(Inactive) Women's Masters (70-74) 58 kg",
    "(Inactive) Women's Masters (70-74) 63 kg",
    "(Inactive) Women's Masters (70-74) 69 kg",
    "(Inactive) Women's Masters (70-74) 75 kg",
    "(Inactive) Women's Masters (70-74) 90 kg",
    "(Inactive) Women's Masters (70-74) +90 kg",
    "(Inactive) Men's Masters (70-74) 56 kg",
    "(Inactive) Men's Masters (70-74) 62 kg",
    "(Inactive) Men's Masters (70-74) 69 kg",
    "(Inactive) Men's Masters (70-74) 77 kg",
    "(Inactive) Men's Masters (70-74) 85 kg",
    "(Inactive) Men's Masters (70-74) 94 kg",
    "(Inactive) Men's Masters (70-74) 105 kg",
    "(Inactive) Men's Masters (70-74) +105 kg",
    "(Inactive) Men's Masters (75-79) 56 kg",
    "(Inactive) Men's Masters (75-79) 62 kg",
    "(Inactive) Men's Masters (75-79) 69 kg",
    "(Inactive) Men's Masters (75-79) 77 kg",
    "(Inactive) Men's Masters (75-79) 85 kg",
    "(Inactive) Men's Masters (75-79) 94 kg",
    "(Inactive) Men's Masters (75-79) 105 kg",
    "(Inactive) Men's Masters (75-79) +105 kg",
    "(Inactive) Women's Masters (75+) 48 kg",
    "(Inactive) Open Women's 48 kg",
    "(Inactive) Women's Masters (75+) 53 kg",
    "(Inactive) Women's Masters (75+) 58 kg",
    "(Inactive) Women's Masters (75+) 63 kg",
    "(Inactive) Women's Masters (75+) 69 kg",
    "(Inactive) Women's Masters (75+) 75 kg",
    "(Inactive) Open Women's 53 kg",
    "(Inactive) Open Women's 58 kg",
    "(Inactive) Open Women's 63 kg",
    "(Inactive) Open Women's 69 kg",
    "(Inactive) Open Women's 75 kg",
    "(Inactive) Open Women's 90 kg",
    "(Inactive) Women's Masters (75+) 90 kg",
    "(Inactive) Open Women's +90 kg",
    "(Inactive) Women's Masters (75+) +90 kg",
    "(Inactive) Open Men's 56 kg",
    "(Inactive) Men's Masters (80+) 56 kg",
    "(Inactive) Open Men's 62 kg",
    "(Inactive) Men's Masters (80+) 62 kg",
    "(Inactive) Open Men's 69 kg",
    "(Inactive) Men's Masters (80+) 69 kg",
    "(Inactive) Open Men's 77 kg",
    "(Inactive) Men's Masters (80+) 77 kg",
    "(Inactive) Open Men's 85 kg",
    "(Inactive) Men's Masters (80+) 85 kg",
    "(Inactive) Men's Masters (80+) 94 kg",
    "(Inactive) Open Men's 94 kg",
    "(Inactive) Open Men's 105 kg",
    "(Inactive) Men's Masters (80+) 105 kg",
    "(Inactive) Open Men's+105 kg",
    "(Inactive) Men's Masters (80+) +105 kg",
    "(Inactive) Women's 13 Under Age Group 30kg",
    "(Inactive) Women's 13 Under Age Group 33kg",
    "(Inactive) Women's 13 Under Age Group 36kg",
    "(Inactive) Women's 13 Under Age Group 40kg",
    "(Inactive) Women's 13 Under Age Group 45kg",
    "(Inactive) Women's 13 Under Age Group 49kg",
    "(Inactive) Women's 13 Under Age Group 55kg",
    "(Inactive) Women's 13 Under Age Group 59kg",
    "(Inactive) Women's 13 Under Age Group 64kg",
    "(Inactive) Women's 13 Under Age Group +64kg",
    "(Inactive) Men's 13 Under Age Group 32kg",
    "(Inactive) Men's 13 Under Age Group 36kg",
    "(Inactive) Men's 13 Under Age Group 39kg",
    "(Inactive) Men's 13 Under Age Group 44kg",
    "(Inactive) Men's 13 Under Age Group 49kg",
    "(Inactive) Men's 13 Under Age Group 55kg",
    "(Inactive) Men's 13 Under Age Group 61kg",
    "(Inactive) Men's 13 Under Age Group 67kg",
    "(Inactive) Men's 13 Under Age Group 73kg",
    "(Inactive) Men's 13 Under Age Group +73kg",
    "(Inactive) Women's 14-15 Age Group 36kg",
    "(Inactive) Women's 14-15 Age Group 40kg",
    "(Inactive) Women's 14-15 Age Group 45kg",
    "(Inactive) Women's 14-15 Age Group 49kg",
    "(Inactive) Women's 14-15 Age Group 55kg",
    "(Inactive) Women's 14-15 Age Group 59kg",
    "(Inactive) Women's 14-15 Age Group 64kg",
    "(Inactive) Women's 14-15 Age Group 71kg",
    "(Inactive) Women's 14-15 Age Group 76kg",
    "(Inactive) Women's 14-15 Age Group +76kg",
    "(Inactive) Men's 14-15 Age Group 39kg",
    "(Inactive) Men's 14-15 Age Group 44kg",
    "(Inactive) Men's 14-15 Age Group 49kg",
    "(Inactive) Men's 14-15 Age Group 55kg",
    "(Inactive) Men's 14-15 Age Group 61kg",
    "(Inactive) Men's 14-15 Age Group 67kg",
    "(Inactive) Men's 14-15 Age Group 73kg",
    "(Inactive) Men's 14-15 Age Group 81kg",
    "(Inactive) Men's 14-15 Age Group 89kg",
    "(Inactive) Men's 14-15 Age Group +89kg",
    "(Inactive) Women's 16-17 Age Group 40kg",
    "(Inactive) Women's 16-17 Age Group 45kg",
    "(Inactive) Women's 16-17 Age Group 49kg",
    "(Inactive) Women's 16-17 Age Group 55kg",
    "(Inactive) Women's 16-17 Age Group 59kg",
    "(Inactive) Women's 16-17 Age Group 64kg",
    "(Inactive) Women's 16-17 Age Group 71kg",
    "(Inactive) Women's 16-17 Age Group 76kg",
    "(Inactive) Women's 16-17 Age Group 81kg",
    "(Inactive) Women's 16-17 Age Group +81kg",
    "(Inactive) Men's 16-17 Age Group 49kg",
    "(Inactive) Men's 16-17 Age Group 55kg",
    "(Inactive) Men's 16-17 Age Group 61kg",
    "(Inactive) Men's 16-17 Age Group 67kg",
    "(Inactive) Men's 16-17 Age Group 73kg",
    "(Inactive) Men's 16-17 Age Group 81kg",
    "(Inactive) Men's 16-17 Age Group 89kg",
    "(Inactive) Men's 16-17 Age Group 96kg",
    "(Inactive) Men's 16-17 Age Group 102kg",
    "(Inactive) Men's 16-17 Age Group +102kg",
    "(Inactive) Junior Women's 45kg",
    "(Inactive) Junior Women's 49kg",
    "(Inactive) Junior Women's 55kg",
    "(Inactive) Junior Women's 59kg",
    "(Inactive) Junior Women's 64kg",
    "(Inactive) Junior Women's 71kg",
    "(Inactive) Junior Women's 76kg",
    "(Inactive) Junior Women's 81kg",
    "(Inactive) Junior Women's 87kg",
    "(Inactive) Junior Women's +87kg",
    "(Inactive) Junior Men's 55kg",
    "(Inactive) Junior Men's 61kg",
    "(Inactive) Junior Men's 67kg",
    "(Inactive) Junior Men's 73kg",
    "(Inactive) Junior Men's 81kg",
    "(Inactive) Junior Men's 89kg",
    "(Inactive) Junior Men's 96kg",
    "(Inactive) Junior Men's 102kg",
    "(Inactive) Junior Men's 109kg",
    "(Inactive) Junior Men's +109kg",
    "(Inactive) Women's Masters (35-39) 45kg",
    "(Inactive) Women's Masters (35-39) 49kg",
    "(Inactive) Women's Masters (35-39) 55kg",
    "(Inactive) Women's Masters (35-39) 59kg",
    "(Inactive) Women's Masters (35-39) 64kg",
    "(Inactive) Women's Masters (35-39) 71kg",
    "(Inactive) Women's Masters (35-39) 76kg",
    "(Inactive) Women's Masters (35-39) 81kg",
    "(Inactive) Women's Masters (35-39) 87kg",
    "(Inactive) Women's Masters (35-39) +87kg",
    "(Inactive) Men's Masters (35-39) 55kg",
    "(Inactive) Men's Masters (35-39) 61kg",
    "(Inactive) Men's Masters (35-39) 67kg",
    "(Inactive) Men's Masters (35-39) 73kg",
    "(Inactive) Men's Masters (35-39) 81kg",
    "(Inactive) Men's Masters (35-39) 89kg",
    "(Inactive) Men's Masters (35-39) 96kg",
    "(Inactive) Men's Masters (35-39) 102kg",
    "(Inactive) Men's Masters (35-39) 109kg",
    "(Inactive) Men's Masters (35-39) +109kg",
    "(Inactive) Women's Masters (40-44) 45kg",
    "(Inactive) Women's Masters (40-44) 49kg",
    "(Inactive) Women's Masters (40-44) 55kg",
    "(Inactive) Women's Masters (40-44) 59kg",
    "(Inactive) Women's Masters (40-44) 64kg",
    "(Inactive) Women's Masters (40-44) 71kg",
    "(Inactive) Women's Masters (40-44) 76kg",
    "(Inactive) Women's Masters (40-44) 81kg",
    "(Inactive) Women's Masters (40-44) 87kg",
    "(Inactive) Women's Masters (40-44) +87kg",
    "(Inactive) Men's Masters (40-44) 55kg",
    "(Inactive) Men's Masters (40-44) 61kg",
    "(Inactive) Men's Masters (40-44) 67kg",
    "(Inactive) Men's Masters (40-44) 73kg",
    "(Inactive) Men's Masters (40-44) 81kg",
    "(Inactive) Men's Masters (40-44) 89kg",
    "(Inactive) Men's Masters (40-44) 96kg",
    "(Inactive) Men's Masters (40-44) 102kg",
    "(Inactive) Men's Masters (40-44) 109kg",
    "(Inactive) Men's Masters (40-44) +109kg",
    "(Inactive) Women's Masters (45-49) 45kg",
    "(Inactive) Women's Masters (45-49) 49kg",
    "(Inactive) Women's Masters (45-49) 55kg",
    "(Inactive) Women's Masters (45-49) 59kg",
    "(Inactive) Women's Masters (45-49) 64kg",
    "(Inactive) Women's Masters (45-49) 71kg",
    "(Inactive) Women's Masters (45-49) 76kg",
    "(Inactive) Women's Masters (45-49) 81kg",
    "(Inactive) Women's Masters (45-49) 87kg",
    "(Inactive) Women's Masters (45-49) +87kg",
    "(Inactive) Men's Masters (45-49) 55kg",
    "(Inactive) Men's Masters (45-49) 61kg",
    "(Inactive) Men's Masters (45-49) 67kg",
    "(Inactive) Men's Masters (45-49) 73kg",
    "(Inactive) Men's Masters (45-49) 81kg",
    "(Inactive) Men's Masters (45-49) 89kg",
    "(Inactive) Men's Masters (45-49) 96kg",
    "(Inactive) Men's Masters (45-49) 102kg",
    "(Inactive) Men's Masters (45-49) 109kg",
    "(Inactive) Men's Masters (45-49) +109kg",
    "(Inactive) Women's Masters (50-54) 45kg",
    "(Inactive) Women's Masters (50-54) 49kg",
    "(Inactive) Women's Masters (50-54) 55kg",
    "(Inactive) Women's Masters (50-54) 59kg",
    "(Inactive) Women's Masters (50-54) 64kg",
    "(Inactive) Women's Masters (50-54) 71kg",
    "(Inactive) Women's Masters (50-54) 76kg",
    "(Inactive) Women's Masters (50-54) 81kg",
    "(Inactive) Women's Masters (50-54) 87kg",
    "(Inactive) Women's Masters (50-54) +87kg",
    "(Inactive) Men's Masters (50-54) 55kg",
    "(Inactive) Men's Masters (50-54) 61kg",
    "(Inactive) Men's Masters (50-54) 67kg",
    "(Inactive) Men's Masters (50-54) 73kg",
    "(Inactive) Men's Masters (50-54) 81kg",
    "(Inactive) Men's Masters (50-54) 89kg",
    "(Inactive) Men's Masters (50-54) 96kg",
    "(Inactive) Men's Masters (50-54) 102kg",
    "(Inactive) Men's Masters (50-54) 109kg",
    "(Inactive) Men's Masters (50-54) +109kg",
    "(Inactive) Women's Masters (55-59) 45kg",
    "(Inactive) Women's Masters (55-59) 49kg",
    "(Inactive) Women's Masters (55-59) 55kg",
    "(Inactive) Women's Masters (55-59) 59kg",
    "(Inactive) Women's Masters (55-59) 64kg",
    "(Inactive) Women's Masters (55-59) 71kg",
    "(Inactive) Women's Masters (55-59) 76kg",
    "(Inactive) Women's Masters (55-59) 81kg",
    "(Inactive) Women's Masters (55-59) 87kg",
    "(Inactive) Women's Masters (55-59) +87kg",
    "(Inactive) Men's Masters (55-59) 55kg",
    "(Inactive) Men's Masters (55-59) 61kg",
    "(Inactive) Men's Masters (55-59) 67kg",
    "(Inactive) Men's Masters (55-59) 73kg",
    "(Inactive) Men's Masters (55-59) 81kg",
    "(Inactive) Men's Masters (55-59) 89kg",
    "(Inactive) Men's Masters (55-59) 96kg",
    "(Inactive) Men's Masters (55-59) 102kg",
    "(Inactive) Men's Masters (55-59) 109kg",
    "(Inactive) Men's Masters (55-59) +109kg",
    "(Inactive) Women's Masters (60-64) 45kg",
    "(Inactive) Women's Masters (60-64) 49kg",
    "(Inactive) Women's Masters (60-64) 55kg",
    "(Inactive) Women's Masters (60-64) 59kg",
    "(Inactive) Women's Masters (60-64) 64kg",
    "(Inactive) Women's Masters (60-64) 71kg",
    "(Inactive) Women's Masters (60-64) 76kg",
    "(Inactive) Women's Masters (60-64) 81kg",
    "(Inactive) Women's Masters (60-64) 87kg",
    "(Inactive) Women's Masters (60-64) +87kg",
    "(Inactive) Men's Masters (60-64) 55kg",
    "(Inactive) Men's Masters (60-64) 61kg",
    "(Inactive) Men's Masters (60-64) 67kg",
    "(Inactive) Men's Masters (60-64) 73kg",
    "(Inactive) Men's Masters (60-64) 81kg",
    "(Inactive) Men's Masters (60-64) 89kg",
    "(Inactive) Men's Masters (60-64) 96kg",
    "(Inactive) Men's Masters (60-64) 102kg",
    "(Inactive) Men's Masters (60-64) 109kg",
    "(Inactive) Men's Masters (60-64) +109kg",
    "(Inactive) Women's Masters (65-69) 45kg",
    "(Inactive) Women's Masters (65-69) 49kg",
    "(Inactive) Women's Masters (65-69) 55kg",
    "(Inactive) Women's Masters (65-69) 59kg",
    "(Inactive) Women's Masters (65-69) 64kg",
    "(Inactive) Women's Masters (65-69) 71kg",
    "(Inactive) Women's Masters (65-69) 76kg",
    "(Inactive) Women's Masters (65-69) 81kg",
    "(Inactive) Women's Masters (65-69) 87kg",
    "(Inactive) Women's Masters (65-69) +87kg",
    "(Inactive) Men's Masters (65-69) 55kg",
    "(Inactive) Men's Masters (65-69) 61kg",
    "(Inactive) Men's Masters (65-69) 67kg",
    "(Inactive) Men's Masters (65-69) 73kg",
    "(Inactive) Men's Masters (65-69) 81kg",
    "(Inactive) Men's Masters (65-69) 89kg",
    "(Inactive) Men's Masters (65-69) 96kg",
    "(Inactive) Men's Masters (65-69) 102kg",
    "(Inactive) Men's Masters (65-69) 109kg",
    "(Inactive) Men's Masters (65-69) +109kg",
    "(Inactive) Women's Masters (70-74) 45kg",
    "(Inactive) Women's Masters (70-74) 49kg",
    "(Inactive) Women's Masters (70-74) 55kg",
    "(Inactive) Women's Masters (70-74) 59kg",
    "(Inactive) Women's Masters (70-74) 64kg",
    "(Inactive) Women's Masters (70-74) 71kg",
    "(Inactive) Women's Masters (70-74) 76kg",
    "(Inactive) Women's Masters (70-74) 81kg",
    "(Inactive) Women's Masters (70-74) 87kg",
    "(Inactive) Women's Masters (70-74) +87kg",
    "(Inactive) Men's Masters (70-74) 55kg",
    "(Inactive) Men's Masters (70-74) 61kg",
    "(Inactive) Men's Masters (70-74) 67kg",
    "(Inactive) Men's Masters (70-74) 73kg",
    "(Inactive) Men's Masters (70-74) 81kg",
    "(Inactive) Men's Masters (70-74) 89kg",
    "(Inactive) Men's Masters (70-74) 96kg",
    "(Inactive) Men's Masters (70-74) 102kg",
    "(Inactive) Men's Masters (70-74) 109kg",
    "(Inactive) Men's Masters (70-74) +109kg",
    "(Inactive) Men's Masters (75-79) 55kg",
    "(Inactive) Men's Masters (75-79) 61kg",
    "(Inactive) Men's Masters (75-79) 67kg",
    "(Inactive) Men's Masters (75-79) 73kg",
    "(Inactive) Men's Masters (75-79) 81kg",
    "(Inactive) Men's Masters (75-79) 89kg",
    "(Inactive) Men's Masters (75-79) 96kg",
    "(Inactive) Men's Masters (75-79) 102kg",
    "(Inactive) Men's Masters (75-79) 109kg",
    "(Inactive) Men's Masters (75-79) +109kg",
    "(Inactive) Open Women's 45kg",
    "(Inactive) Women's Masters (75+) 45kg",
    "(Inactive) Open Women's 49kg",
    "(Inactive) Women's Masters (75+) 49kg",
    "(Inactive) Women's Masters (75+) 55kg",
    "(Inactive) Open Women's 55kg",
    "(Inactive) Women's Masters (75+) 59kg",
    "(Inactive) Open Women's 59kg",
    "(Inactive) Open Women's 64kg",
    "(Inactive) Women's Masters (75+) 64kg",
    "(Inactive) Open Women's 71kg",
    "(Inactive) Women's Masters (75+) 71kg",
    "(Inactive) Open Women's 76kg",
    "(Inactive) Women's Masters (75+) 76kg",
    "(Inactive) Open Women's 81kg",
    "(Inactive) Women's Masters (75+) 81kg",
    "(Inactive) Open Women's 87kg",
    "(Inactive) Women's Masters (75+) 87kg",
    "(Inactive) Open Women's +87kg",
    "(Inactive) Women's Masters (75+) +87kg",
    "(Inactive) Open Men's 55kg",
    "(Inactive) Men's Masters (80+) 55kg",
    "(Inactive) Open Men's 61kg",
    "(Inactive) Men's Masters (80+) 61kg",
    "(Inactive) Open Men's 67kg",
    "(Inactive) Men's Masters (80+) 67kg",
    "(Inactive) Open Men's 73kg",
    "(Inactive) Men's Masters (80+) 73kg",
    "(Inactive) Open Men's 81kg",
    "(Inactive) Men's Masters (80+) 81kg",
    "(Inactive) Open Men's 89kg",
    "(Inactive) Men's Masters (80+) 89kg",
    "(Inactive) Men's Masters (80+) 96kg",
    "(Inactive) Open Men's 96kg",
    "(Inactive) Open Men's 102kg",
    "(Inactive) Men's Masters (80+) 102kg",
    "(Inactive) Open Men's 109kg",
    "(Inactive) Men's Masters (80+) 109kg",
    "(Inactive) Open Men's +109kg",
    "(Inactive) Men's Masters (80+) +109kg"
]


#print(len(all_active_weight_classes))
#print(len(all_old_weight_classes))
def scrape_rankings_page(weight_classes_heats):
    with sync_playwright() as p:
        page = log_into_USAW(p)
        print("PASSED log_into_USAW")

        click_months_back(page)
        print("PASSED click_months_back")


        # SCRAPING
        all_data = []
        # This loop is for each BW category
        for heat in weight_classes_heats:
            for category in heat:
                all_data = scrape_weight_class(page, all_data, category)
                
                bar = "#" * (heat.index(category) + 1) + "-" * (len(heat) - heat.index(category) - 1)
                print(f"\r{bar} PASSED {category}\n", end="", flush=True)
                '''
                # Specify weight class first
                page.click("#weight_class")
                print("Clicked weight class")

                # Wait for dropdown options to appear
                page.wait_for_selector("div.v-list-item")
                print("Waited for dropdown")

                # Click the option you want (e.g., category name)
                #page.get_by_role("option", name=category, exact=True).click()
                options = page.get_by_role("option").all()
                for opt in options:
                    text = opt.inner_text().strip()
                    if text == category:  # exact match
                        opt.click()
                        break

                print("Clicked the category we wanted")


                # press apply
                page.locator("button:has-text('Apply')").click()
                print("clicked apply")

                while True:
                    # Then scrape each row 
                    page.wait_for_selector("tr.row-clickable")
                    athlete_rows = page.locator("tr.row-clickable")
                    # 8th class="text-start" is where the membership # is
                    # 4th is where name is 
                    # (lets scrape it, which might be wasteful later, but be a double check to make sure that membership # and name align correctly)
                    
                    # Scrape each row on current page
                    print(f"The number of athlete rows we expect {athlete_rows.count()}")

                    for i in range(athlete_rows.count()):
                        row = athlete_rows.nth(i)
                        row_located = row.locator("td div")
                        if row_located.count() < 8:
                            break
                        name = row_located.nth(3).inner_text().strip()         # 4th column (index 3)
                        age = row_located.nth(5).inner_text().strip()          # 6th column (index 5)
                        membership = row_located.nth(7).inner_text().strip()   # 8th column (index 7)

                        print("-----")
                        print(name, age, membership)

                    # go into each row (click on it)
                        with page.context.expect_page() as new_page_info:
                            row.click()
                        ath_page = new_page_info.value
                        ath_page.wait_for_load_state("networkidle")
                        # wait for the results table to appear
                        ath_page.wait_for_selector("table thead:has-text('Lifter')")
                        print(f"Clicked athlete row {i+1}")
                        

                        # scrape the new athlete page
                        while True:
                            page_num = 1
                            max_page = 100
                            each_ath_rows = ath_page.locator("div.v-data-table__wrapper tbody tr")
                            # Loop through each row
                            for i in range(each_ath_rows.count()):
                                new_row = each_ath_rows.nth(i).locator("td div")
                                values = [new_row.nth(j).inner_text().strip() for j in range(new_row.count())]

                                # Insert age, membership and name into each data row
                                values.insert(0, age)
                                values.insert(0, membership)
                                values.insert(0, name)

                                
                                all_data.append(values)
                                    
                            #print(all_data)

                            # move to next athlete page
                            next_button = ath_page.locator("button[aria-label='Next page']:not([disabled])")

                            # repeat until there are no new pages
                            if next_button.count() == 0:
                                print("No more pages for this athlete.")
                                break

                            next_button.click()

                                # Wait for page to change - use a more robust wait
                            try:
                                # Wait for the table to update (rows might change)
                                ath_page.wait_for_timeout(1000)  # Brief pause
                                ath_page.wait_for_selector("table tbody tr:not([style*='display: none'])", timeout=10000)
                                print("Page updated successfully")
                            except Exception as e:
                                print(f"Page update wait failed: {e}")
                                # Try alternative wait
                                try:
                                    ath_page.wait_for_function(
                                        """() => {
                                            const rows = document.querySelectorAll('table tbody tr');
                                            return rows.length > 0;
                                        }""",
                                        timeout=10000
                                    )
                                except:
                                    print("Table did not update after Next — breaking.")
                                    break
                            
                            page_num += 1

                        # delete current page
                        ath_page.close()
                        print(f"Completed scraping {name}")

                        df = pd.DataFrame(all_data)
                        df.to_csv("athlete_results.csv", index=False)

                    # now, move to next page of meets
                    next_page_of_meets = page.locator("button[aria-label='Next page']:not([disabled])")
                    if next_page_of_meets.count() == 0:
                        print("No more pages of meets")
                        break
                    try:
                        current_page_text = page.locator("button[aria-current='true']").inner_text(timeout=5000)
                        print(f"Current page: {current_page_text}")
                    except:
                        print("Could not get current page number, but proceeding...")
                    next_page_of_meets.click()

                    try: 
                        # Wait for the table to update (rows might change)
                        page.wait_for_timeout(1000)  # Brief pause
                        page.wait_for_selector("table tbody tr:not([style*='display: none'])", timeout=10000)
                        print("Page updated successfully")
                    except Exception as e:
                            print(f"Page update wait failed: {e}")
                            # Try alternative wait
                            try:
                                ath_page.wait_for_function(
                                    """() => {
                                        const rows = document.querySelectorAll('table tbody tr');
                                        return rows.length > 0;
                                    }""",
                                    timeout=10000
                                )
                            except:
                                print("Table did not update after Next — breaking.")
                                break


                print(all_data)
                print(f"done scraping athletes for {category}")                         
                '''

                # Move back and open "wifi symbol", prep for next category
                #page.wait_for_selector("#form__date_range_start")
                #print("waited for the filters button to appear")

                # Click on that date range
                page.get_by_role("button", name="Show Filters").click()
                #print("Clicked show filters (wifi button)")\

                # We want to save to the csv after every weight class is correctly completed
                df = pd.DataFrame(all_data)
                df.to_csv("athlete_results.csv", index=False)

def log_into_USAW(p):
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://usaweightlifting.sport80.com/v/1023105/r/rankings?filters=eyJkYXRlX3JhbmdlX3N0YXJ0IjoiMjAyNS0wMS0wMSIsImRhdGVfcmFuZ2VfZW5kIjoiMjAyNS0xMi0zMSJ9")

    email = "odavis.1555@gmail.com"
    password = "SLifts557whoza"

    # Fill out username and password fields
    page.fill("#username", email)
    page.press("#username", "Tab") 
    page.fill("#password", password)

    page.press("#password", "Enter")
    # Make sure we don't need to have a device confirmation
    try: 
        page.wait_for_selector("#deviceToken", timeout=10000)
    except:
        pass
    if page.locator("#deviceToken").count() > 0:
        print("Device confirmation required — waiting for code...")
        security_code = input("Give us the security code :")

        page.fill("#deviceToken", security_code)
        page.press("#deviceToken", "Enter")
    return page

def click_months_back(page):
    page.wait_for_selector("#form__date_range_start")


    # Click on that date range
    #page.get_by_role("button", name="Show Filters").click()
    #print("Clicked show filters (wifi button)")\
    
    page.click("#form__date_range_start")

    # loop to click into the desired past
    # Last month of meets is in January 2011, so we can assume even one athlete could've lifted one time back then
    target_month = "January 2025"
    month_button = page.locator("div.v-date-picker-header__value button").first
    while True:
        current_month = month_button.inner_text()
        #print(current_month)
        time.sleep(0.5)
        if current_month == target_month:
            print(f"Reached {target_month}")
            break

        page.get_by_role("button", name="Previous month").click()
        #print("Clicked backwards")

    #print("You made it out of the loop!")

    page.locator("button.v-btn", has_text="1").first.click()
    #print("clicked the 1st of the month")

    page.get_by_role("button", name="OK").click()
    #print("clicked OK")

def scrape_weight_class(page, all_data, category):
    # CHOSING WC AND CLICKING IT 

    # Click on the section labeled "weight_class"
    page.click("#weight_class")
    # Wait for dropdown options to appear
    page.wait_for_selector("div.v-list-item")
    # Click the option we want (category name)
    options = page.get_by_role("option").all()
    for opt in options:
        text = opt.inner_text().strip()
        if text == category:  # exact match
            opt.click()
            break

    # press apply
    page.locator("button:has-text('Apply')").click()



    # Now we're on a page of athletes - just their names and max totals. 
    # We're going to loop until we stop seeing new pages of athletes
    total_fails = 0
    scrape_all_athletes_in_wc(page, all_data, category, total_fails)
    return all_data

# Now we're on a page of athletes - just their names and max totals. 
# We're going to loop until we stop seeing new pages of athletes     
# And then we stop adding to all_data 
def scrape_all_athletes_in_wc(page, all_data, category, total_fails):
    try:
        while True:
            # Wait for athlete_rows to appear
            page.wait_for_selector("tr.row-clickable")
            athlete_rows = page.locator("tr.row-clickable")
            

            # Now we'll loop through all the rows on this current page of athletes
            # Each iteration in the loop checks a row, clicked into it (individual athlete)
            # Then loops for all rows in individual_athlete (each meet they've attended) and scrapes

            #print(f"The number of athlete rows we expect {athlete_rows.count()}")
            for i in range(athlete_rows.count()):
                # current row
                row = athlete_rows.nth(i)
                row_located = row.locator("td div")

                # if the current row doesn't exist, we stop.
                if row_located.count() < 8:
                    break

                # get name, age, membership number
                name = row_located.nth(3).inner_text().strip()         # 4th column (index 3)
                age = row_located.nth(5).inner_text().strip()          # 6th column (index 5)
                membership = row_located.nth(7).inner_text().strip()   # 8th column (index 7)

                # click on the row now, new page is now called ath_page
                with page.context.expect_page() as new_page_info:
                    row.click()
                ath_page = new_page_info.value
                ath_page.wait_for_load_state("networkidle")
                # wait for the individual athlete results table to appear
                ath_page.wait_for_selector("table thead:has-text('Lifter')")
                

                # scrape each individual athlete fully
                while True:
                    page_num = 1
                    max_page = 100
                    each_ath_rows = ath_page.locator("div.v-data-table__wrapper tbody tr")
                    # Loop through each row
                    for i in range(each_ath_rows.count()):
                        new_row = each_ath_rows.nth(i).locator("td div")
                        values = [new_row.nth(j).inner_text().strip() for j in range(new_row.count())]

                        # Insert age, membership and name into each data row
                        values.insert(0, age)
                        values.insert(0, membership)
                        values.insert(0, name)

                        
                        all_data.append(values)
                            
                    #print(all_data)

                    # move to next athlete page
                    next_button = ath_page.locator("button[aria-label='Next page']:not([disabled])")

                    # repeat until there are no new pages
                    if next_button.count() == 0:
                        #print("No more pages for this athlete.")
                        break

                    next_button.click()

                    # Wait for page to change - use a more robust wait
                    try:
                        # Wait for the table to update (rows might change)
                        ath_page.wait_for_timeout(1000)  # Brief pause
                        ath_page.wait_for_selector("table tbody tr:not([style*='display: none'])", timeout=10000)
                        #print("Page updated successfully")
                    except Exception as e:
                        #print(f"Page update wait failed: {e}")
                        # Try alternative wait
                        try:
                            ath_page.wait_for_function(
                                """() => {
                                    const rows = document.querySelectorAll('table tbody tr');
                                    return rows.length > 0;
                                }""",
                                timeout=10000
                            )
                        except:
                            #print("Table did not update after Next — breaking.")
                            break
                    
                    page_num += 1

                # delete current athlete page
                ath_page.close()

                df = pd.DataFrame(all_data)
                df.to_csv("athlete_results.csv", index=False)

            # now, move to next page of athletes
            next_page_of_meets = page.locator("button[aria-label='Next page']:not([disabled])")
            if next_page_of_meets.count() == 0:
                #print("No more pages of athletes")
                break
            try:
                current_page_text = page.locator("button[aria-current='true']").inner_text(timeout=5000)
                #print(f"Current page: {current_page_text}")
            except:
                pass
            next_page_of_meets.click()

            # wait for the table to update to next page (we want rows to have changed)
            try: 
                page.wait_for_timeout(1000)  # Brief pause
                page.wait_for_selector("table tbody tr:not([style*='display: none'])", timeout=10000)
            except Exception as e:
                    # Try alternative wait
                    try:
                        ath_page.wait_for_function(
                            """() => {
                                const rows = document.querySelectorAll('table tbody tr');
                                return rows.length > 0;
                            }""",
                            timeout=10000
                        )
                    except:
                        break
        
    except:
        # If we fail, tell in terminal, but retry scrape_all_athletes_in_wc
        print(f"FAILED - {category} - retrying scrape_all_athletes_in_wc")
        total_fails += 1
        print(f"Fail count now at {total_fails}")
        if total_fails > 5:
            print("Fail count now over 5. Returning 0 for current weight class, thereby passing.")
            return 0
        scrape_all_athletes_in_wc(page)

if __name__ == '__main__':
    scrape_rankings_page(all_active_weight_classes)