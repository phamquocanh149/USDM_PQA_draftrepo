# Adapted from ../RasterizeUSDMforDryad.R; preserves the 0.5-degree grid.
args <- commandArgs(trailingOnly = FALSE)
script <- sub('^--file=', '', args[grepl('^--file=', args)])
script_dir <- dirname(normalizePath(script))
root <- dirname(dirname(script_dir))
out <- file.path(dirname(script_dir), "data")
if (!dir.exists(out)) dir.create(out, recursive = TRUE)
suppressPackageStartupMessages({library(sf); library(raster); library(maps)})
shp_dir <- file.path(root, "bronze", "data", "shp")
if (!dir.exists(shp_dir)) shp_dir <- file.path(root, "shp")
files <- sort(list.files(shp_dir, pattern = "^USDM_[0-9]{8}\\.shp$", recursive = TRUE, full.names = TRUE))
dates <- sub('^USDM_([0-9]{8})\\.shp$', '\\1', basename(files))
keep <- dates >= '20200101' & dates <= '20221231'
files <- files[keep]; dates <- dates[keep]
stopifnot(length(files) > 0, !anyDuplicated(dates))
source <- st_read(files[1], quiet = TRUE)
template <- raster(ncols = 120, nrows = 50, xmn = -125, xmx = -65,
                   ymn = 25, ymx = 50, crs = st_crs(source)$wkt)
# Same state map and five exclusions as the original script.
states <- st_as_sf(maps::map('state', fill = TRUE, plot = FALSE))
states <- st_transform(states, st_crs(source))
us.grid <- rasterize(as(states, 'Spatial'), template, field = 1)
row_names <- c(LETTERS, paste0(LETTERS[1:24], LETTERS[1:24]))
for (cell in c('S2','S105','EE97','KK88','RR85')) {
  r <- match(sub('[0-9]+$', '', cell), row_names)
  c <- as.integer(sub('^[A-Z]+', '', cell))
  us.grid[r,c] <- NA
}
wh <- which(!is.na(values(us.grid)))
coord.use <- xyFromCell(template, wh)
labels <- paste0(row_names[rowFromCell(template, wh)], colFromCell(template, wh))
dz <- as.matrix(dist(coord.use))
A <- 1L * (dz > 0.01 & dz < 0.71)
dimnames(A) <- list(labels, labels)
write.csv(A, file.path(out, 'A.csv'))
rm(dz)
dm <- vector('list', length(files))
rows <- vector('list', length(files))
for (q in seq_along(files)) {
  usdm <- st_read(files[q], quiet = TRUE)
  stopifnot('DM' %in% names(usdm), all(!is.na(usdm$DM)), all(usdm$DM %in% 0:4))
  usdm <- st_transform(usdm, st_crs(source))
  # Offset DM so 0 denotes no drought, 1 denotes D0, ..., 5 denotes D4.
  usdm$level <- as.integer(usdm$DM) + 1L
  rr <- rasterize(as(usdm, 'Spatial'), template, field = 'level')
  v <- values(rr)[wh]
  v[is.na(v)] <- 0L
  stopifnot(all(v %in% 0:5))
  rr[] <- NA_real_; rr[wh] <- v
  dm[[q]] <- rr
  rows[[q]] <- data.frame(time = dates[q], grid = labels,
    lon = coord.use[,1], lat = coord.use[,2],
    drought = ifelse(v == 0, '0', paste0('D', v - 1L)))
  cat(sprintf('[%d/%d] %s\n', q, length(files), dates[q])); flush.console()
}
data <- do.call(rbind, rows)
stopifnot(nrow(data) == length(files) * length(wh), !anyNA(data),
          !anyDuplicated(data[c('time','grid')]),
          all(data$drought %in% c('0', paste0('D',0:4))))
write.csv(data, file.path(out, 'usdmfinal.csv'), row.names = FALSE)
write.csv(data.frame(time = dates, source = files), file.path(out, 'input_manifest.csv'), row.names = FALSE)
save(data, dm, A, us.grid, template, labels, coord.use, files, dates,
     file = file.path(out, 'USDMRasterized.rda'))
capture.output(sessionInfo(), file = file.path(out, 'sessionInfo.txt'))
report <- c(sprintf('Weeks: %d; range: %s - %s', length(files), min(dates), max(dates)),
 sprintf('Valid grid cells: %d; rows: %d', length(wh), nrow(data)),
 'Requested range: 20200101 - 20221231. Available inputs end on 20220628.',
 'Grid: 120 x 50; 0.5 degrees; contiguous-US mask; original five sea-cell exclusions.',
 'drought: 0 = no drought; D0-D4 = DM classes. Rasters: 0 = no drought; 1-5 = D0-D4.',
 'Source shapefiles are unchanged.', capture.output(table(data$drought)))
writeLines(report, file.path(out, 'validation.txt'))
cat(paste(report, collapse = '\n'), '\n')

