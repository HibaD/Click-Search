<!DOCTYPE html>
<html lang="en">

 <head>
 	<meta charset="utf-8">
    <title>Search Engine</title>
 </head>

 <body>
	<div class="Go Back">
		<form method="GET" action="/">
			% if email not in ['Guest']:
				<input type="Submit" class="btn" name="Logout" value="Logout"/>
			% end
			<input type="Submit" class="btn" name="Search" value="Back to Search"/>{{email}}</input>
		</form>
	</div>
	<div class="main">
		<h1>This is not a valid web page.</h1>
	</div>
 </body>

</html>
