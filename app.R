library(shiny)
library(leaflet)
library(sf)
library(dplyr)

# Define UI
ui <- fluidPage(
  tags$head(
    tags$style(
      HTML("
        body {
          background-color: #abf5bf;
        }
      ")
    )
  ),
  titlePanel("Demographics and Airbnb Average Price by ZIP code"),
  sidebarLayout(
    sidebarPanel(
      selectInput("selected_variable", "Select Demographic Variable:", NULL),
      checkboxInput("toggle_bivariate", "Toggle Bivariate Choropleth", FALSE)  # Add checkbox to toggle bivariate choropleth
    ),
    mainPanel(
      leafletOutput("myMap", height = "600px")  # Increase map size
    )
  ),
  fluidRow(
    column(width = 12,
           wellPanel(
             h3("Map Information"),
             p("This map displays demographics and Airbnb average prices segmented by ZIP code in New York City."),
             p("The dropdown menu allows you to select a demographic variable to visualize on the map."),
             p("The bivariate choropleth toggle allows you to display a combination of the selected demographic variable and average price on the map."),
             p("The color of each ZIP code represents the value of the selected demographic variable, with darker shades indicating higher values."),
             p("If the bivariate choropleth toggle is enabled, the color of each ZIP code represents a combination of the selected demographic variable and average price."),
             p("Hover over a ZIP code to view its information, including the ZIP code itself, the value of the selected demographic variable, and the average price."),
             
           )
    )
  )
)

server <- function(input, output, session) {
  
  # Load your datasets
  demographics <- read.csv("C:\\Users\\John Ledesma\\Downloads\\Demographic_Statistics_By_Zip_Code.csv")
  shapefile <- st_read("C:\\Users\\John Ledesma\\Downloads\\ZIP_CODE_040114 (1)\\ZIP_CODE_040114.shp")
  abnb <- read.csv("C:\\Users\\John Ledesma\\Documents\\abnb_final.csv")
  
  # Ensure that the ZIP code in demographics data and abnb data is character and not factor
  demographics$JURISDICTION.NAME <- as.character(demographics$JURISDICTION.NAME)
  abnb$ZIPCODE <- as.character(abnb$ZIPCODE)
  
  # Make sure ZIPCODE in shapefile is also character to prevent join issues
  shapefile$ZIPCODE <- as.character(shapefile$ZIPCODE)
  
  # Transform the CRS to longitude-latitude
  shapefile <- st_transform(shapefile, crs = 4326)
  
  # Join the shapefile with the demographics data and the Airbnb data
  joined_data <- shapefile %>% 
    left_join(demographics, by = c("ZIPCODE" = "JURISDICTION.NAME")) %>%
    left_join(abnb, by = "ZIPCODE")
  
  # Prepare the names for dropdown menu
  percent_names <- grep("PERCENT", names(demographics), value = TRUE)
  new_names <- tolower(sub("PERCENT.", "", percent_names))
  names_list <- setNames(percent_names, new_names)  # Set original names as values for corresponding new names
  
  # Remove "Totals" and "Unknown" from the dropdown menu options
  names_list <- names_list[!grepl("TOTAL|UNKNOWN", names_list)]
  
  # Update dropdown options
  updateSelectInput(session, "selected_variable", choices = names_list)
  
  output$myMap <- renderLeaflet({
    req(input$selected_variable)  # Ensure that input$selected_variable is not NULL
    
    # Remove non-finite values from the color palette domain
    valid_values <- joined_data[[input$selected_variable]]
    valid_values <- valid_values[is.finite(valid_values)]
    
    pal <- colorNumeric(palette = c("lightblue", "darkblue"), domain = valid_values)
    
    price_pal <- colorNumeric(palette = "YlOrRd", domain = joined_data$Average_Price)
    
    leaflet(joined_data) %>% 
      addProviderTiles("CartoDB.Positron") %>%  # Set the background tiles to white
      addPolygons(
        fillColor = ~if (input$toggle_bivariate) {
          return(colorRampPalette(c("lightblue", "darkblue", "yellow", "red"))(n = 100)[
            findInterval(joined_data[[input$selected_variable]], sort(joined_data[[input$selected_variable]])) +
              findInterval(joined_data$Average_Price, sort(joined_data$Average_Price))
          ])
        } else {
          pal(joined_data[[input$selected_variable]])
        },
        fillOpacity = 0.7, 
        color = "#BDBDC3", 
        weight = 1,
        popup = paste("ZIP code: ", joined_data$ZIPCODE, 
                      "<br/>Demographic Value: ", joined_data[[input$selected_variable]],
                      "<br/>Average Price: ", joined_data$Average_Price),
        highlightOptions = highlightOptions(
          color = "white", 
          weight = 2,
          bringToFront = TRUE)
      ) %>%
      addLegend(
        position = "bottomright",  # Set the position of the legend
        pal = if (input$toggle_bivariate) { colorRampPalette(c("lightblue", "darkblue", "yellow", "red"))(n = 100) } else { pal },  # Use the color palette for the legend
        values = if (input$toggle_bivariate) { 
          seq(0, max(joined_data[[input$selected_variable]], joined_data$Average_Price), length.out = 101)[-1]
        } else {
          joined_data[[input$selected_variable]]
        },  # Use the values from the selected variable
        title = "Legend",  # Set the title of the legend
        opacity = 0.7
      )
  })
  
}

# Run the application 
shinyApp(ui = ui, server = server)

            
