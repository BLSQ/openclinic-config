<%
    response.sendRedirect(request.getRequestURI().replaceAll(request.getServletPath(),"")+"/login.jsp?Title=VBG&Dir=projects/gbvm/");
%>